"""Testes sem rede; somente fixtures sintéticas e arquivos privados temporários."""
import json
import pytest
from transporte.gobus_staging import stage, cities

def callback(name, body):
    return name+'('+json.dumps(body,ensure_ascii=False)+');'

def write(folder,name,callback_name,obj):
    (folder/name).write_text(callback(callback_name,obj),encoding='utf-8')

@pytest.fixture
def fixture(tmp_path):
    src=tmp_path/'captures';src.mkdir()
    write(src,'cidades.jsonp','retornoJSONCidades',
          {'sucesso':True,'cidade':["{'sg':'CAN','desc':'CANOAS'},{'sg':'POA','desc':'PORTO ALEGRE'}"]})
    write(src,'linhas.jsonp','retornoJSONListaLinhas',
          {'sucesso':True,'linhas':"[{'cod':'17','sgl':'05000','nom':'MATHIAS VELHO/CENTRO'}]"})
    write(src,'paradas.jsonp','retornoJSONH',
          {'sucesso':True,'paradas':[{'cod':1,'x':-51.20,'y':-29.91,'desc':'PARADA A'},
                                    {'cod':2,'x':-51.19,'y':-29.92,'desc':'PARADA B'}]})
    write(src,'itinerario.jsonp','retornoJSONItinerario',
          {'sucesso':True,'itinerarios':[{'coordX':-51.20,'coordY':-29.91},
                                        {'coordX':-51.19,'coordY':-29.92}]})
    manifest={'municipality_code':'4304606','city':'CAN','authorization_confirmed':True,
              'city_confirmed':True,'reference_date':'2026-10-30',
              'cities_file':'cidades.jsonp','lines_file':'linhas.jsonp',
              'mapping':[{'siu_line_id':'17','ngs_route_id':'05000','crosswalk_approved':True,
                          'stops_file':'paradas.jsonp',
                          'itineraries':[{'id':'123','direction':'Centro','relation_approved':True,
                                          'file':'itinerario.jsonp'}]}]}
    network={'routes':[{'id':'05000','name':'Mathias Velho/Centro'}]}
    return src,manifest,network

def test_cities_extraction(fixture):
    src,_,_=fixture
    rows=cities((src/'cidades.jsonp').read_text())
    assert rows==[{'code':'CAN','name':'CANOAS'},{'code':'POA','name':'PORTO ALEGRE'}]

def test_staging_routes_stops_crosswalk(fixture):
    src,manifest,network=fixture
    result=stage(manifest,source_dir=src,ngs_network=network)
    assert result['summary']['itinerary_count']==1
    assert result['summary']['stop_count']==2
    assert result['summary']['status']=='pending_publication_review'
    feature=result['routes']['features'][0]
    assert feature['properties']['route_id']=='05000'
    assert feature['geometry']['coordinates'][0]==[-51.2,-29.91]
    assert feature['properties']['status']=='staging'
    assert len(result['evidence'])==4

@pytest.mark.parametrize('change',[
    {'authorization_confirmed':False},
    {'city_confirmed':False},
    {'city':'BHZ'},
    {'municipality_code':'4305108'},
])
def test_requires_authorization_scope(fixture,change):
    src,manifest,network=fixture
    manifest.update(change)
    with pytest.raises(ValueError):
        stage(manifest,source_dir=src,ngs_network=network)

def test_reject_unapproved_crosswalk(fixture):
    src,manifest,network=fixture
    manifest['mapping'][0]['crosswalk_approved']=False
    with pytest.raises(ValueError,match='aprova'):
        stage(manifest,source_dir=src,ngs_network=network)

def test_reject_unknown_ngs_line(fixture):
    src,manifest,network=fixture
    manifest['mapping'][0]['ngs_route_id']='99999'
    with pytest.raises(ValueError):
        stage(manifest,source_dir=src,ngs_network=network)

def test_reject_unapproved_itinerary_relation(fixture):
    src,manifest,network=fixture
    manifest['mapping'][0]['itineraries'][0]['relation_approved']=False
    with pytest.raises(ValueError):
        stage(manifest,source_dir=src,ngs_network=network)

def test_reject_out_of_area_route(fixture):
    src,manifest,network=fixture
    write(src,'itinerario.jsonp','retornoJSONItinerario',
          {'sucesso':True,'itinerarios':[{'coordX':-43.90,'coordY':-19.93},
                                        {'coordX':-43.95,'coordY':-19.94}]})
    with pytest.raises(ValueError,match='área operacional'):
        stage(manifest,source_dir=src,ngs_network=network)

def test_reject_path_traversal(fixture):
    src,manifest,network=fixture
    manifest['cities_file']='../fora.jsonp'
    with pytest.raises(ValueError,match='fora'):
        stage(manifest,source_dir=src,ngs_network=network)

def test_reject_city_mismatch(fixture):
    src,manifest,network=fixture
    write(src,'cidades.jsonp','retornoJSONCidades',
          {'sucesso':True,'cidade':["{'sg':'BHZ','desc':'BELO HORIZONTE'}"]})
    with pytest.raises(ValueError,match='não confirma'):
        stage(manifest,source_dir=src,ngs_network=network)

def test_reject_duplicate_itinerary(fixture):
    src,manifest,network=fixture
    manifest['mapping'][0]['itineraries'] *= 2
    with pytest.raises(ValueError,match='duplicado'):
        stage(manifest,source_dir=src,ngs_network=network)

def test_mpa_numeric_city_id_filters_other_municipalities(fixture):
    src,manifest,network=fixture
    write(src,'cidades-linhas.jsonp','retornoJSONCidadesLinhas',
          {'sucesso':True,'cidade':["{'cod':'4','desc':'CANOAS'},{'cod':'9','desc':'OUTRO MUNICÍPIO'}"]})
    write(src,'linhas.jsonp','retornoJSONListaLinhas',
          {'sucesso':True,'linhas':"[{'cod':'17','sgl':'05000','nom':'MATHIAS VELHO/CENTRO','codcid':4,'praca':'MPA'},{'cod':'20','sgl':'999','nom':'OUTRO','codcid':9,'praca':'MPA'}]"})
    manifest.pop('cities_file')
    manifest['line_cities_file']='cidades-linhas.jsonp'
    manifest['canoas_city_id']='4'
    assert stage(manifest,source_dir=src,ngs_network=network)['summary']['matched_route_count']==1
    manifest['mapping'][0]['siu_line_id']='20'
    with pytest.raises(ValueError,match='inexistente'):
        stage(manifest,source_dir=src,ngs_network=network)

def test_mpa_rejects_unverified_city_code(fixture):
    src,manifest,network=fixture
    write(src,'cidades-linhas.jsonp','retornoJSONCidadesLinhas',
          {'sucesso':True,'cidade':["{'cod':'4','desc':'CANOAS'}"]})
    manifest.pop('cities_file')
    manifest['line_cities_file']='cidades-linhas.jsonp'
    manifest['canoas_city_id']='9'
    with pytest.raises(ValueError,match='não confirmado'):
        stage(manifest,source_dir=src,ngs_network=network)
