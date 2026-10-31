"""Importação explícita de percursos reais. Não geocodifica logradouros nem adivinha linhas."""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from shapely.geometry import shape
from .collect import dump
from .geo import valid_coordinate
from .http import utcnow


def route_index(network):
    aliases={}
    for route in network['routes']:
        for alias in {route['id'],route['code']}:
            key=str(alias).lstrip('0') or '0'
            if key in aliases and aliases[key]!=route['id']:
                raise ValueError('Código de linha ambíguo no catálogo: '+key)
            aliases[key]=route['id']
    return aliases


def validate_geometry(geometry):
    g=shape(geometry)
    if g.geom_type not in ('LineString','MultiLineString') or g.is_empty or not g.is_valid or g.length==0:
        raise ValueError('Percurso precisa ser LineString/MultiLineString válido e não vazio')
    parts=[g] if g.geom_type=='LineString' else g.geoms
    for part in parts:
        for lon,lat,*_ in part.coords:
            if not valid_coordinate(lon,lat):raise ValueError('Coordenada fora da área operacional de validação de Canoas')
    return geometry


def geojson_features(content,aliases):
    document=json.loads(content)
    if document.get('type')!='FeatureCollection':raise ValueError('Esperado GeoJSON FeatureCollection EPSG:4326')
    if document.get('crs'):raise ValueError('Remova CRS legado após converter explicitamente para EPSG:4326')
    result=[]
    for feature in document['features']:
        p=feature.get('properties') or {};alias=str(p.get('route_id','')).lstrip('0') or '0'
        if alias not in aliases:raise ValueError('Linha ausente ou desconhecida: '+str(p.get('route_id')))
        result.append({'type':'Feature','geometry':validate_geometry(feature['geometry']),
                       'properties':{'route_id':aliases[alias],'shape_id':str(p.get('shape_id',len(result))),
                                     'direction':str(p.get('direction','Não informado'))}})
    if not result:raise ValueError('Arquivo sem trajetos; importação não substitui base por vazio')
    return result


def gtfs_features(content,aliases,agency_id,reference_date):
    if not agency_id:raise ValueError('GTFS exige agency_id explícito da rede municipal')
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        if sum(i.file_size for i in z.infolist())>100_000_000:raise ValueError('GTFS descompactado excede 100 MB')
        def rows(name,required=True):
            if name not in z.namelist():
                if required:raise ValueError('Arquivo GTFS ausente: '+name)
                return []
            return list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))
        agencies=rows('agency.txt')
        if not any(a.get('agency_id','')==agency_id for a in agencies):raise ValueError('Agência não encontrada; selecione identificador explícito')
        for info in rows('feed_info.txt',False):
            when=reference_date.replace('-','')
            if info.get('feed_start_date') and when<info['feed_start_date']:raise ValueError('GTFS ainda não vigente na data de referência')
            if info.get('feed_end_date') and when>info['feed_end_date']:raise ValueError('GTFS expirado na data de referência')
        routes={}
        for r in rows('routes.txt'):
            agency=r.get('agency_id') or (agencies[0].get('agency_id') if len(agencies)==1 else None)
            if agency!=agency_id:continue
            alias=str(r.get('route_short_name','')).lstrip('0') or '0'
            if alias in aliases:routes[r['route_id']]=aliases[alias]
        joins={(t['shape_id'],routes[t['route_id']],t.get('direction_id','Não informado'))
               for t in rows('trips.txt') if t['route_id'] in routes and t.get('shape_id')}
        wanted={s for s,_,_ in joins};points={s:[] for s in wanted}
        for p in rows('shapes.txt'):
            if p['shape_id'] in wanted:points[p['shape_id']].append((int(p['shape_pt_sequence']),float(p['shape_pt_lon']),float(p['shape_pt_lat'])))
        result=[]
        for sid,rid,direction in sorted(joins):
            pts=sorted(points[sid]);seq=[p[0] for p in pts]
            if len(pts)<2 or len(seq)!=len(set(seq)):raise ValueError('Shape sem pontos suficientes ou sequência duplicada: '+sid)
            geometry=validate_geometry({'type':'LineString','coordinates':[[x,y] for _,x,y in pts]})
            result.append({'type':'Feature','geometry':geometry,'properties':{'route_id':rid,'shape_id':sid,'direction':direction}})
        if not result:raise ValueError('Nenhum shape associado por código exato à rede municipal cadastrada')
        return result


def import_shapes(root,input_path,*,source_url,source_name,reference_date,municipality_code,agency_id=None,format='geojson'):
    if municipality_code!='4304606':raise ValueError('Escopo exclusivo do município 4304606')
    parsed=urlparse(source_url)
    if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Proveniência exige URL HTTPS sem credenciais')
    if not source_name.strip():raise ValueError('Nome da fonte obrigatório')
    date.fromisoformat(reference_date)
    root=Path(root);path=Path(input_path)
    if path.stat().st_size>20_000_000:raise ValueError('Entrada excede 20 MB')
    content=path.read_bytes();network=json.loads((root/'public/data/network.json').read_text());aliases=route_index(network)
    features=gtfs_features(content,aliases,agency_id,reference_date) if format=='gtfs' else geojson_features(content,aliases)
    now=utcnow();digest=hashlib.sha256(content).hexdigest()
    for feature in features:
        feature['properties'].update({'source_url':source_url,'source_name':source_name,'source_sha256':digest,
            'fetched_at':now,'reference_date':reference_date,'municipality_code':municipality_code,
            'status':'reference','method':'import-shapes-0.2.0','agency_id':agency_id or ''})
    result={'type':'FeatureCollection','features':features,'status':'reference','generated_at':now,
        'description':'Geometrias fornecidas para referência. Importação não equivale a homologação municipal ou comprovação de vigência operacional.'}
    # Evidência local imutável por conteúdo; preservar versões antes de substituir a publicação ativa.
    archive=root/'var/shape-history';archive.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(result,ensure_ascii=False,sort_keys=True).encode()
    for payload in [encoded, (root/'public/data/route-shapes.geojson').read_bytes() if (root/'public/data/route-shapes.geojson').exists() else b'']:
        if payload:
            snapshot=archive/(hashlib.sha256(payload).hexdigest()+'.geojson')
            if not snapshot.exists():snapshot.write_bytes(payload)
    source_copy=archive/(digest+('.zip' if format=='gtfs' else '.source.geojson'))
    if not source_copy.exists():source_copy.write_bytes(content)
    dump(root/'public/data/route-shapes.geojson',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--format',choices=['geojson','gtfs'],default='geojson')
    for name in ['source-url','source-name','reference-date','municipality-code']:p.add_argument('--'+name,required=True)
    p.add_argument('--agency-id');p.add_argument('--root',default=str(Path(__file__).resolve().parents[2]));args=vars(p.parse_args());input_path=args.pop('input');root=args.pop('root')
    result=import_shapes(root,input_path,**args)
    from .tiles import build_pmtiles
    build_pmtiles(root)
    print(json.dumps({'event':'shapes_imported','features':len(result['features']),'routes':len({f['properties']['route_id'] for f in result['features']})}))

if __name__=='__main__':main()
