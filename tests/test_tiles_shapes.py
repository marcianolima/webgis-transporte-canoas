"""Fixtures SYNTHETIC só em diretórios temporários; arquivo publicado contém apenas bases reais."""
import csv
import gzip
import hashlib
import io
import json
import zipfile
from pathlib import Path
import mercantile
import mapbox_vector_tile
import pytest
from pmtiles.reader import Reader
from pmtiles.tile import TileType, Compression
from transporte.tiles import build_pmtiles
from transporte.import_shapes import import_shapes,gtfs_features,geojson_features,route_index
ROOT=Path(__file__).resolve().parents[1]


def fixture_geo():
    return {'type':'FeatureCollection','features':[{'type':'Feature','properties':{'route_id':'SYNTHETIC','shape_id':'SYNTHETIC'},'geometry':{'type':'LineString','coordinates':[[-51.19,-29.91],[-51.18,-29.90]]}}]}


def temporary_root(tmp_path):
    data=tmp_path/'public/data';data.mkdir(parents=True)
    network={'routes':[{'id':'SYNTHETIC','code':'SYNTHETIC'}]}
    (data/'network.json').write_text(json.dumps(network))
    polygon={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'BAIRRO':'SYNTHETIC'},'geometry':{'type':'Polygon','coordinates':[[[-51.2,-29.92],[-51.17,-29.92],[-51.17,-29.89],[-51.2,-29.89],[-51.2,-29.92]]]}}]}
    for name in ['bairros-oficiais.geojson','censo2022-setores.geojson','boundary.geojson']:(data/name).write_text(json.dumps(polygon))
    (data/'stops.geojson').write_text('{"type":"FeatureCollection","features":[]}')
    return data


def test_public_pmtiles_header_hash_metadata_and_tile():
    data=ROOT/'public/data';blob=(data/'transporte-canoas.pmtiles').read_bytes();reader=Reader(lambda offset,length:blob[offset:offset+length])
    header=reader.header();manifest=json.loads((data/'map-manifest.json').read_text())
    assert header['tile_type']==TileType.MVT and header['tile_compression']==Compression.GZIP
    assert header['min_zoom']==8 and header['max_zoom']==13
    assert manifest['sha256']==hashlib.sha256(blob).hexdigest() and manifest['bytes']==len(blob)
    metadata=reader.metadata();assert metadata['layer_feature_counts']['bairros']==18 and metadata['layer_feature_counts']['setores']==659
    assert metadata['boundary_is_official'] is False
    tile=mercantile.tile(-51.18,-29.9,13);decoded=mapbox_vector_tile.decode(gzip.decompress(reader.get(tile.z,tile.x,tile.y)))
    assert decoded['bairros']['features'] and decoded['setores']['features']
    for name,sha in metadata['source_hashes'].items():assert hashlib.sha256((data/name).read_bytes()).hexdigest()==sha


def test_builder_deterministic_and_line_roundtrip(tmp_path):
    data=temporary_root(tmp_path);(data/'route-shapes.geojson').write_text(json.dumps(fixture_geo()))
    first=build_pmtiles(tmp_path);blob=(data/'transporte-canoas.pmtiles').read_bytes();second=build_pmtiles(tmp_path)
    assert first['sha256']==second['sha256'] and first['route_geometry_count']==1
    reader=Reader(lambda offset,length:blob[offset:offset+length]);tile=mercantile.tile(-51.185,-29.905,12)
    decoded=mapbox_vector_tile.decode(gzip.decompress(reader.get(tile.z,tile.x,tile.y)),default_options={'y_coord_down':True})
    feature=decoded['linhas']['features'][0];assert feature['properties']['route_id']=='SYNTHETIC'
    # No MVT, norte fica em y menor. Detecta inversão vertical na codificação.
    coords=feature['geometry']['coordinates'];assert coords[0][0]<coords[-1][0] and coords[0][1]>coords[-1][1]
    assert first['route_status']['SYNTHETIC']['shape_count']==1


def test_import_requires_provenance_and_preserves_hash(tmp_path):
    data=temporary_root(tmp_path);source=tmp_path/'SYNTHETIC.geojson';source.write_text(json.dumps(fixture_geo()))
    args=dict(source_url='https://example.invalid/SYNTHETIC',source_name='SYNTHETIC',reference_date='2026-10-30',municipality_code='4304606')
    result=import_shapes(tmp_path,source,**args);p=result['features'][0]['properties']
    assert p['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    assert p['route_id']=='SYNTHETIC' and p['status']=='reference' and p['fetched_at']
    prior=(data/'route-shapes.geojson').read_bytes()
    with pytest.raises(ValueError,match='4304606'):import_shapes(tmp_path,source,**{**args,'municipality_code':'0000000'})
    with pytest.raises(ValueError,match='HTTPS'):import_shapes(tmp_path,source,**{**args,'source_url':'https://user:secret@example.invalid/'})
    assert prior==(data/'route-shapes.geojson').read_bytes()


@pytest.mark.parametrize('change',[ 'unknown','outside','point','empty' ])
def test_geojson_rejects_unusable_geometry(change):
    geo=fixture_geo()
    if change=='unknown':geo['features'][0]['properties']['route_id']='OTHER'
    if change=='outside':geo['features'][0]['geometry']['coordinates'][1]=[0,0]
    if change=='point':geo['features'][0]['geometry']={'type':'Point','coordinates':[-51.18,-29.9]}
    if change=='empty':geo['features']=[]
    with pytest.raises(ValueError):geojson_features(json.dumps(geo),{'SYNTHETIC':'SYNTHETIC'})


def gtfs(end='20261231',duplicate=False):
    files={'agency.txt':'agency_id,agency_name\nMUNICIPAL,SYNTHETIC\nMETRO,SYNTHETIC\n',
           'routes.txt':'route_id,agency_id,route_short_name\na,MUNICIPAL,5000\nb,METRO,5000\n',
           'trips.txt':'route_id,trip_id,shape_id,direction_id\na,a,s,0\nb,b,x,1\n',
           'shapes.txt':'shape_id,shape_pt_sequence,shape_pt_lon,shape_pt_lat\ns,1,-51.19,-29.91\ns,'+('1' if duplicate else '2')+',-51.18,-29.90\nx,1,0,0\nx,2,1,1\n',
           'feed_info.txt':'feed_start_date,feed_end_date\n20260101,'+end+'\n'}
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for name,value in files.items():z.writestr(name,value)
    return stream.getvalue()


def test_gtfs_exact_join_and_agency_scope():
    aliases=route_index({'routes':[{'id':'05000','code':'5000'}]})
    result=gtfs_features(gtfs(),aliases,'MUNICIPAL','2026-10-30')
    assert len(result)==1 and result[0]['properties']['route_id']=='05000'
    assert result[0]['properties']['direction']=='0'
    with pytest.raises(ValueError,match='explícito'):gtfs_features(gtfs(),aliases,None,'2026-10-30')
    with pytest.raises(ValueError,match='expirado'):gtfs_features(gtfs('20261029'),aliases,'MUNICIPAL','2026-10-30')
    with pytest.raises(ValueError,match='duplicada'):gtfs_features(gtfs(duplicate=True),aliases,'MUNICIPAL','2026-10-30')
