import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from transporte.audit import timestamp
from transporte.geo import valid_coordinate, MunicipalReferenceArea
ROOT=Path(__file__).resolve().parents[1];data=ROOT/'public/data'
def main():
    n=json.loads((data/'network.json').read_text());routes={x['id'] for x in n['routes']}
    assert routes and len(routes)==len(n['routes'])
    assert n['schema_version']==1 and timestamp(n['generated_at'])
    keys=[]
    for d in n['departures']:
        assert d['route_id'] in routes and d['source_id']=='sogal-ngs'
        assert timestamp(d['fetched_at']) and len(d['sha256'])==64
        assert d['url'].startswith('https://ngsservicos.com/aplicativos/NgPortais/sogal/scripts/getEspHorario.php?')
        assert 0<=d['service_minute']<2880
        keys.append((d['route_id'],d['date'],d['direction'],d['sequence']))
    assert len(set(keys))==len(keys)
    for file,count in [('bairros-oficiais.geojson',18),('censo2022-setores.geojson',659)]:
        j=json.loads((data/file).read_text());assert len(j['features'])==count
        def coords(x):
            if isinstance(x[0],(int,float)):
                assert valid_coordinate(x[0],x[1])
            else:
                for c in x:coords(c)
        for f in j['features']:coords(f['geometry']['coordinates'])
    for file in data.iterdir():
        assert file.suffix in ('.json','.geojson','.pmtiles'),file.name
        assert file.stat().st_size<20_000_000,(file.name,'artefato > 20 MB')
        if file.suffix!='.pmtiles':assert 'SYNTHETIC' not in file.read_text(),file.name
    manifest=json.loads((data/'map-manifest.json').read_text());tilefile=data/manifest['file']
    assert tilefile.read_bytes().startswith(b'PMTiles')
    assert hashlib.sha256(tilefile.read_bytes()).hexdigest()==manifest['sha256']
    assert tilefile.stat().st_size==manifest['bytes']
    for filename,digest in manifest['source_hashes'].items():assert hashlib.sha256((data/filename).read_bytes()).hexdigest()==digest
    geometries=json.loads((data/'route-shapes.geojson').read_text())['features']
    assert all(f['properties']['route_id'] in routes for f in geometries)
    assert manifest['route_geometry_count']==len({f['properties']['route_id'] for f in geometries})
    area=MunicipalReferenceArea(json.loads((data/'bairros-oficiais.geojson').read_text()))
    for f in geometries:
        p=f['properties'];assert p['status']=='reference' and p.get('homologated') is not True
        assert p['source_url'].startswith(('https://','http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/'))
        assert timestamp(p['fetched_at']) and len(p['source_sha256'])==64
        if p.get('source')=='TACOM-GoBus':
            quality=area.line(f);assert quality['local_length_pct']>=80 and quality['max_boundary_distance_m']<=1500
    stop_features=json.loads((data/'stops.geojson').read_text())['features'];ids=[]
    for f in stop_features:
        p=f['properties'];ids.append(p['stop_id']);assert p['status']=='reference' and p['homologated'] is False
        assert set(p['route_ids']).issubset(routes) and p['route_ids']
        assert area.point(*f['geometry']['coordinates']) and timestamp(p['fetched_at']) and len(p['source_sha256'])==64
    assert len(ids)==len(set(ids)) and manifest['layers']['paradas']==len(ids)
    for name in ['route-shapes.geojson','stops.geojson','transport-geography.json']:
        assert not any(key in (data/name).read_text() for key in ['numVeicGestor','vehicle_id','"body":'])
    assert not json.loads((data/'boundary.geojson').read_text())['features'][0]['properties']['is_official_municipal_boundary']
    print(json.dumps({'status':'passed','routes':len(routes),'departures':len(keys),'dates':len(n['source_dates']),'public_bytes':sum(p.stat().st_size for p in data.iterdir())}))
if __name__=='__main__':main()
