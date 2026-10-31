"""Testes offline com dados sintéticos dos contratos extraídos do APK GoBus."""
import json
import pytest
from transporte.gobus import request_path, lines, stops, itinerary, vehicles, predictions

def reply(callback, data):
    return f'{callback}({json.dumps(data,ensure_ascii=False)});'

def test_path_contracts():
    assert request_path('linhas') == 'buscarLinhas/retornoJSONListaLinhas'
    assert request_path('itinerario', itinerario=123, cidade='CAN') == 'V3/buscarItinerario/123/0/CAN/retornoJSONItinerario'
    assert request_path('veiculos', itinerario=123, cidade='CAN').endswith('/retornoJSONVeiculos')
    assert request_path('previsoes', parada=456, acessivel='false', cidade='CAN').endswith('/retornoJSON')
    assert request_path('paradas_proximas', longitude=-51.18, latitude=-29.91, cidade='CAN').startswith('V3/buscarParadasProximas/-51.18/-29.91/')

@pytest.mark.parametrize('name,kwargs', [
    ('veiculos', {'itinerario':'../123','cidade':'CAN'}),
    ('itinerario', {'itinerario':1,'cidade':'BHZ/../../'}),
    ('previsoes', {'parada':1,'acessivel':'yes','cidade':'CAN'}),
    ('cidades', {'cidade':'CAN'}),
])
def test_blocks_invalid_paths(name, kwargs):
    with pytest.raises(ValueError):
        request_path(name,**kwargs)

def test_lines_legacy():
    raw = reply('retornoJSONListaLinhas',{'sucesso':True,
        'linhas':"[{'cod':'42','sgl':'K42','nom':'CENTRO'},{'cod':'43','sgl':'K43','nom':'BAIRRO'}]"})
    assert lines(raw)[0]['cod'] == '42'

def test_route_geojson_order_and_metadata():
    source = reply('retornoJSONItinerario',{'sucesso':True,'itinerarios':[
        {'coordX':'-51,180','coordY':'-29,920'},
        {'coordX':-51.175,'coordY':-29.925}]})
    geo = itinerary(source,'123')
    assert geo['geometry']['coordinates'] == [[-51.18,-29.92],[-51.175,-29.925]]
    assert geo['properties']['homologated'] is False

def test_stops_and_vehicles_with_unknown_gps_timestamp():
    s = stops(reply('retornoJSONH',{'sucesso':True,
        'paradas':[{'cod':11,'x':-51.2,'y':-29.9,'desc':'PARADA'}]}))
    assert s[0]['longitude'] == -51.2
    v = vehicles(reply('retornoJSONVeiculos',{'sucesso':True,
        'veiculos':[{'numVeicGestor':'110','lat':-29.9,'long':-51.2,'direcao':4}]}))
    assert v[0]['source_timestamp'] is None
    assert v[0]['homologated'] is False

def test_predictions_and_unsafe_jsonp():
    p = predictions(reply('retornoJSON',{'sucesso':True,
        'previsoes':[{'sgLin':'K1','prev':'5 min','codItinerario':2}]}))
    assert p[0]['prev'] == '5 min'
    with pytest.raises(ValueError):
        vehicles('cb({});alert(1)')
    with pytest.raises(ValueError):
        itinerary(reply('cb',{'sucesso':True,
            'itinerarios':[{'coordX':1,'coordY':1}]}),'1')
