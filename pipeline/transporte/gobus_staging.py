"""Extração e homologação offline dos dados GoBus de Canoas.

Entradas são capturas feitas com autorização. Uma correspondência SIU→NGS
explícita e uma cidade confirmada são obrigatórias. NENHUMA publicação automática.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from .gobus import payload, lines, stops, itinerary
from .parsing import legacy_rows
from .geo import valid_coordinate

MUNICIPALITY = '4304606'

def cities(raw: str) -> list[dict]:
    source = payload(raw).get('cidade')
    values = legacy_rows(source)
    result = []
    for row in values:
        code = str(row.get('sg', '')).strip().upper()
        if code and row.get('desc'):
            result.append({'code': code, 'name': str(row['desc']).strip()})
    return result

def _read(root: Path, name: str) -> tuple[str, str]:
    """Limita leitura ao diretório privado de capturas, sem path traversal."""
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('Caminho da captura inválido')
    base = root.resolve()
    target = (base / name).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError('Captura fora da pasta autorizada')
    if target.stat().st_size > 5_000_000:
        raise ValueError('Captura acima de 5 MB')
    data = target.read_bytes()
    return data.decode('utf-8-sig'), hashlib.sha256(data).hexdigest()

def stage(manifest: dict, *, source_dir: Path, ngs_network: dict) -> dict:
    if manifest.get('municipality_code') != MUNICIPALITY:
        raise ValueError('Escopo municipal deve ser 4304606')
    if manifest.get('city') != 'CAN':
        raise ValueError('Cidade CAN deve estar homologada para esta importação')
    if manifest.get('authorization_confirmed') is not True:
        raise ValueError('Autorização técnica deve estar registrada na entrada')
    if manifest.get('city_confirmed') is not True:
        raise ValueError('Necessária confirmação da cidade no cadastro TACOM')
    if not isinstance(manifest.get('mapping'), list) or not manifest['mapping']:
        raise ValueError('Manifesto não tem correspondências homologadas SIU→NGS')
    if not isinstance(ngs_network.get('routes'), list):
        raise ValueError('Catálogo NGS inválido')

    city_text, city_sha = _read(source_dir, manifest['cities_file'])
    registered = cities(city_text)
    if not any(r['code'] == 'CAN' and 'CANOAS' in r['name'].upper() for r in registered):
        raise ValueError('Resposta TACOM não confirma cidade Canoas/CAN')

    line_text, line_sha = _read(source_dir, manifest['lines_file'])
    source_lines = {str(row['cod']): row for row in lines(line_text)}
    ngs_routes = {str(row['id']): row for row in ngs_network['routes']}
    geo = []
    all_stops = {}
    seen_itineraries = {}
    evidence = [
        {'kind': 'cidades', 'sha256': city_sha},
        {'kind': 'linhas', 'sha256': line_sha}
    ]
    mappings = []
    for item in manifest['mapping']:
        source_id = str(item.get('siu_line_id', ''))
        route_id = str(item.get('ngs_route_id', ''))
        if source_id not in source_lines or route_id not in ngs_routes:
            raise ValueError('Correspondência envolve linha inexistente: '+source_id+'/'+route_id)
        if not item.get('crosswalk_approved') is True:
            raise ValueError('Correspondência SIU/NGS ainda não aprovada: '+source_id)
        matches = [s for s in mappings if s['siu_line_id'] == source_id]
        if matches:
            raise ValueError('SIU line repetida no manifesto')
        mappings.append({'siu_line_id': source_id, 'siu_name': source_lines[source_id]['nom'],
                         'siu_code': source_lines[source_id]['sgl'], 'ngs_route_id': route_id,
                         'ngs_name': ngs_routes[route_id]['name']})
        stop_file = item.get('stops_file')
        if stop_file:
            raw, digest = _read(source_dir, stop_file)
            evidence.append({'kind': 'paradas', 'siu_line_id': source_id, 'sha256': digest})
            for stop in stops(raw):
                if 'longitude' not in stop or not valid_coordinate(stop['longitude'], stop['latitude']):
                    raise ValueError('Parada fora da área operacional ou sem coordenada')
                key = stop['stop_id']
                coordinates = [stop['longitude'], stop['latitude']]
                if key in all_stops:
                    if all_stops[key]['geometry']['coordinates'] != coordinates:
                        raise ValueError('Parada repetida com coordenadas divergentes: '+key)
                    related = all_stops[key]['properties']['route_ids']
                    if route_id not in related: related.append(route_id)
                else:
                    all_stops[key] = {'type': 'Feature',
                        'geometry': {'type': 'Point', 'coordinates': coordinates},
                        'properties': {'stop_id': key, 'siu': stop.get('siu'), 'name': stop.get('label'),
                                       'route_ids': [route_id], 'source': 'TACOM-GoBus', 'municipality_code': MUNICIPALITY}}
        for entry in item.get('itineraries', []):
            itinerary_id = str(entry.get('id', ''))
            if not itinerary_id.isdecimal():
                raise ValueError('Código de itinerário deve ser numérico')
            if not entry.get('relation_approved') is True:
                raise ValueError('Relação itinerário-linha/sentido sem aprovação: '+itinerary_id)
            direction = str(entry.get('direction', '')).strip()
            if not direction:
                raise ValueError('Sentido/variante deve ser informado explicitamente')
            if itinerary_id in seen_itineraries and seen_itineraries[itinerary_id] != (route_id, direction):
                raise ValueError('Itinerário SIU associado a linhas/sentidos conflitantes')
            if itinerary_id in seen_itineraries:
                raise ValueError('Itinerário duplicado')
            seen_itineraries[itinerary_id] = (route_id, direction)
            raw, digest = _read(source_dir, entry.get('file'))
            feature = itinerary(raw, itinerary_id)
            pts = feature['geometry']['coordinates']
            if not all(valid_coordinate(lon, lat) for lon, lat in pts):
                raise ValueError('Itinerário fora da área operacional de Canoas: '+itinerary_id)
            if len(set(map(tuple, pts))) < 2:
                raise ValueError('Itinerário degenerado')
            feature['properties'].update({
                'route_id': route_id, 'shape_id': 'SIU-'+itinerary_id,
                'direction': direction, 'siu_line_id': source_id,
                'source_sha256': digest, 'municipality_code': MUNICIPALITY,
                'status': 'staging', 'source_name': 'TACOM/GoBus',
                'reference_date': manifest.get('reference_date'),
                'authorization_confirmed': True})
            geo.append(feature)
            evidence.append({'kind': 'itinerario', 'siu_line_id': source_id,
                             'itinerary_id': itinerary_id, 'sha256': digest})

    for feature in all_stops.values():
        feature['properties']['route_ids'].sort()
    coverage = {
        'ngs_route_count': len(ngs_routes),
        'matched_route_count': len({i['ngs_route_id'] for i in mappings}),
        'itinerary_count': len(geo),
        'stop_count': len(all_stops),
        'status': 'pending_publication_review',
        'warning': 'Dados em staging; não demonstram viagens realizadas, GPS atual ou pontualidade.'
    }
    return {
        'routes': {'type': 'FeatureCollection', 'features': geo, 'status': 'staging'},
        'stops': {'type': 'FeatureCollection', 'features': sorted(all_stops.values(),key=lambda f:f['properties']['stop_id']), 'status': 'staging'},
        'crosswalk': mappings,
        'evidence': evidence,
        'summary': coverage
    }

def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--manifest', type=Path, required=True)
    cli.add_argument('--source-dir', type=Path, required=True)
    cli.add_argument('--network', type=Path, default=Path('public/data/network.json'))
    cli.add_argument('--output', type=Path, default=Path('var/gobus/staging'))
    args = cli.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    result = stage(manifest, source_dir=args.source_dir,
                   ngs_network=json.loads(args.network.read_text(encoding='utf-8')))
    args.output.mkdir(parents=True, exist_ok=True)
    for key, value in result.items():
        (args.output / (key+'.json' if key not in ('routes','stops') else key+'.geojson')).write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
