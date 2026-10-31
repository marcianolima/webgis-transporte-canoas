"""Sonda de catálogo GoBus: garante limite fixo de duas chamadas e resposta sanitizada."""
import json
import pytest
from scripts.gobus_probe_catalogue import discover

class Reply:
    status=200
    def __init__(self,text):
        self.raw=text.encode()
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def read(self,n):return self.raw[:n]

class Fake:
    def __init__(self,payloads):
        self.payloads=payloads
        self.calls=[]
    def open(self,request,timeout):
        self.calls.append(request.full_url)
        return Reply(self.payloads[len(self.calls)-1])

def jsonp(callback,data):
    return callback+'('+json.dumps(data,ensure_ascii=False)+');'

def test_only_two_requests_with_can():
    service=Fake([
        jsonp('retornoJSONCidades',{'sucesso':True,
            'cidade':["{'sg':'CAN','desc':'CANOAS'}"]}),
        jsonp('retornoJSONListaLinhas',{'sucesso':True,
            'linhas':"[{'cod':'17','sgl':'05000','nom':'MATHIAS VELHO','praca':'CAN'}]"})])
    data=discover(service,sleep=lambda _:None)
    assert len(service.calls)==2
    assert data['city_verified'] is True
    assert data['explicit_can_lines']==1
    assert data['gps_collected'] is False

def test_does_not_query_lines_if_can_missing():
    service=Fake([jsonp('retornoJSONCidades',{'sucesso':True,
        'cidade':["{'sg':'BHZ','desc':'BELO HORIZONTE'}"]})])
    with pytest.raises(ValueError,match='CAN_not_confirmed'):
        discover(service,sleep=lambda _:None)
    assert len(service.calls)==1

def test_bad_response_no_second_request():
    service=Fake(['function(){alert(1)}();'])
    with pytest.raises(ValueError,match='invalid_schema'):
        discover(service,sleep=lambda _:None)
    assert len(service.calls)==1
