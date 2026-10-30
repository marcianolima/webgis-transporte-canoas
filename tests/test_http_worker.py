"""Fixtures sintéticas locais; sem consulta remota em testes."""
import urllib.error
from datetime import datetime,timezone
import httpx
import pytest
from transporte.http import Fetcher
from transporte.worker import once
from transporte.store import Store

class Response:
    status=200
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def read(self,_):return b'{"SYNTHETIC":true}'

def test_http_cache_and_provenance(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr('urllib.request.urlopen',lambda *args,**kw:(calls.append(args),Response())[1])
    fetcher=Fetcher(tmp_path,interval=0)
    a=fetcher.get('https://example.invalid/SYNTHETIC');b=fetcher.get('https://example.invalid/SYNTHETIC')
    assert len(calls)==1 and a['sha256']==b['sha256'] and fetcher.records[-1]['cache_hit']

def test_no_retry_for_forbidden(tmp_path,monkeypatch):
    calls=[]
    def fail(*args,**kw):
        calls.append(1);raise urllib.error.HTTPError('https://example.invalid',403,'Forbidden',{},None)
    monkeypatch.setattr('urllib.request.urlopen',fail)
    with pytest.raises(urllib.error.HTTPError):Fetcher(tmp_path,interval=0).get('https://example.invalid/SYNTHETIC')
    assert len(calls)==1

def test_retry_is_bounded(tmp_path,monkeypatch):
    calls=[]
    def fail(*args,**kw):
        calls.append(1);raise urllib.error.HTTPError('https://example.invalid',503,'Unavailable',{},None)
    monkeypatch.setattr('urllib.request.urlopen',fail);monkeypatch.setattr('time.sleep',lambda _:None)
    with pytest.raises(urllib.error.HTTPError):Fetcher(tmp_path,interval=0,retries=2).get('https://example.invalid/SYNTHETIC')
    assert len(calls)==3

def test_worker_accepts_only_municipal_data_and_deduplicates(tmp_path):
    store=Store('sqlite:///'+str(tmp_path/'worker.sqlite'));store.initialize()
    value={'source_id':'SYNTHETIC','vehicle_id':'TEST','route_id':'TEST','longitude':-51.18,'latitude':-29.92,
           'observed_at':datetime.now(timezone.utc).isoformat(),'scope':'municipal','municipality_code':'4304606'}
    client=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'vehicles':[value,value|{'scope':'metropolitan'}]})))
    a=once(store,client,'https://example.invalid');b=once(store,client,'https://example.invalid')
    assert a['accepted']==1 and a['rejected']==1 and a['status']=='partial'
    assert b['accepted']==0 and len(store.history())==1

def test_worker_sanitizes_failures(tmp_path):
    store=Store('sqlite:///'+str(tmp_path/'worker.sqlite'));store.initialize()
    client=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(403,text='SYNTHETIC-SECRET')))
    value=once(store,client,'https://example.invalid','SYNTHETIC-SECRET')
    assert value['status']=='failed' and 'SECRET' not in value['message']
