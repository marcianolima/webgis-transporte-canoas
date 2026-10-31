"""Capturador GoBus MPA/codcid=4: chamadas limitadas e sem acesso externo."""
import json
import pytest
from scripts.gobus_capture_geography import capture

class Reply:
    status=200
    def __init__(self,text):self.raw=text.encode()
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def read(self,n):return self.raw[:n]

class Fake:
    def __init__(self,entries):self.entries=entries;self.calls=[]
    def open(self,req,timeout):
        self.calls.append(req.full_url)
        return Reply(self.entries[len(self.calls)-1])

def jp(callback,obj):return callback+'('+json.dumps(obj,ensure_ascii=False)+');'

def source():
    cities=jp('retornoJSONCidadesLinhas',{'sucesso':True,
       'cidade':["{'cod':'4','desc':'CANOAS'},{'cod':'5','desc':'ESTEIO'}"]})
    routes=jp('retornoJSONListaLinhas',{'sucesso':True,
       'linhas':"[{'cod':'17','sgl':'05000','nom':'MATHIAS VELHO','codcid':4,'praca':'MPA'},{'cod':'19','sgl':'180','nom':'OUTRO','codcid':5,'praca':'MPA'}]"})
    stops=jp('retornoJSONH',{'sucesso':True,'paradas':[{'cod':1,'x':-51.2,'y':-29.9}]})
    return [cities,routes,stops]

def plan(line='17'):
    return {'authorized':True,'allow_plain_http':True,'municipality_code':'4304606',
            'city':'MPA','canoas_city_id':'4','resources':[{'kind':'paradas_geograficas','linha':line}]}

def test_capture_mpa_is_private_and_validated(tmp_path):
    client=Fake(source())
    result=capture(plan(),output=tmp_path,opener=client,pause=lambda _:None)
    assert result['canoas_city_id']=='4'
    assert result['municipal_source_lines']==1
    assert len(client.calls)==3
    assert '/17/0/MPA/' in client.calls[-1]
    assert (tmp_path/'capture-manifest.json').exists()
    assert all((tmp_path/r['file']).exists() for r in result['records'])

def test_rejects_city_cross_contamination_before_geography(tmp_path):
    client=Fake(source())
    with pytest.raises(ValueError,match='fora do cadastro municipal'):
        capture(plan('19'),output=tmp_path,opener=client,pause=lambda _:None)
    assert len(client.calls)==2

def test_reject_missing_authorization_before_network(tmp_path):
    client=Fake(source())
    p=plan();p['authorized']=False
    with pytest.raises(ValueError,match='autorização'):
        capture(p,output=tmp_path,opener=client,pause=lambda _:None)
    assert len(client.calls)==0

def test_reject_unapproved_itinerary_before_network(tmp_path):
    client=Fake(source())
    p=plan();p['resources']=[{'kind':'itinerario','itinerario':'123','siu_line_id':'17','relation_approved':False}]
    with pytest.raises(ValueError,match='aprova'):
        capture(p,output=tmp_path,opener=client,pause=lambda _:None)
    assert len(client.calls)==0
