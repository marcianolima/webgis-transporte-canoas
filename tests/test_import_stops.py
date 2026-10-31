"""Importação de paradas: testes sintéticos sem tocar nos dados públicos."""
import json
import pytest
from transporte.import_stops import validate_stops, import_stops

NETWORK={'routes':[{'id':'05000','name':'Mathias Velho/Centro'}]}
STOPS={'type':'FeatureCollection','features':[{'type':'Feature',
    'geometry':{'type':'Point','coordinates':[-51.20,-29.91]},
    'properties':{'stop_id':'11','name':'PARADA A','route_ids':['05000'],'siu':'99'}}]}

def test_valid_stops():
    result=validate_stops(STOPS,NETWORK)
    assert result[0]['properties']['route_ids_csv']=='05000'
    assert result[0]['geometry']['coordinates']==[-51.2,-29.91]

@pytest.mark.parametrize('bad',[
    {'stop_id':None},
    {'route_ids':[]},
    {'route_ids':['99999']},
])
def test_invalid_stop_properties(bad):
    obj=json.loads(json.dumps(STOPS))
    obj['features'][0]['properties'].update(bad)
    with pytest.raises(ValueError):
        validate_stops(obj,NETWORK)

def test_invalid_coordinates():
    obj=json.loads(json.dumps(STOPS))
    obj['features'][0]['geometry']['coordinates']=[-43.9,-19.9]
    with pytest.raises(ValueError):
        validate_stops(obj,NETWORK)

def test_duplicate_stop_rejected():
    obj=json.loads(json.dumps(STOPS))
    obj['features'].append(obj['features'][0])
    with pytest.raises(ValueError):
        validate_stops(obj,NETWORK)

def test_import_stops_requires_approval_and_https(tmp_path):
    public=tmp_path/'public/data';public.mkdir(parents=True)
    (public/'network.json').write_text(json.dumps(NETWORK))
    file=tmp_path/'stops.geojson';file.write_text(json.dumps(STOPS))
    args={'source_url':'https://fonte.example/paradas','source_name':'Fonte oficial',
          'reference_date':'2026-10-30','municipality_code':'4304606'}
    with pytest.raises(ValueError,match='aprovação'):
        import_stops(tmp_path,file,**args)
    with pytest.raises(ValueError,match='HTTPS'):
        import_stops(tmp_path,file,**(args|{'source_url':'http://fonte.example/paradas','approved':True}))
    result=import_stops(tmp_path,file,**(args|{'approved':True}))
    assert result['status']=='reference'
    assert (public/'stops.geojson').exists()
    assert len(list((tmp_path/'var/stop-history').glob('*.source.geojson')))==1
