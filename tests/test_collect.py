"""Pipeline completo sobre fonte sintética confinada ao diretório temporário."""
import json,sqlite3
import pytest
import transporte.collect as module
from transporte.http import utcnow

class SyntheticSource:
    def __init__(self,fetcher):pass
    def dates(self):return [{'DATA':'2026-01-01','DIA':'5'}],{}
    def routes(self,date):return [{'LINHA':'SYNTHETIC','NOME_COMPLETO':'SYNTHETIC'}],{'url':'https://example.invalid','fetched_at':utcnow(),'sha256':'0'*64}
    def schedule(self,route,date):
        return [{'route_id':route,'date':date,'direction':'SYNTHETIC','sequence':0,'time':'06:00','service_minute':360,'fetched_at':utcnow(),'source_id':'SYNTHETIC','sha256':'0'*64,'url':'https://example.invalid'}],{}
    def itinerary(self,route):return [],{}

def test_incremental_static_history_and_execution(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'NGS',SyntheticSource)
    module.collect(days=1,root=tmp_path,interval=0)
    module.collect(days=1,root=tmp_path,interval=0)
    with sqlite3.connect(tmp_path/'var/static-history.sqlite') as db:
        assert db.execute('SELECT COUNT(*) FROM snapshot').fetchone()[0]==2
        assert db.execute("SELECT COUNT(*) FROM run WHERE status='available'").fetchone()[0]==2
    assert json.loads((tmp_path/'public/data/network.json').read_text())['routes'][0]['id']=='SYNTHETIC'

def test_total_failure_preserves_last_publication(tmp_path,monkeypatch):
    class Failure(SyntheticSource):
        def dates(self):raise ValueError('SYNTHETIC failure')
    monkeypatch.setattr(module,'NGS',Failure)
    target=tmp_path/'public/data/network.json';target.parent.mkdir(parents=True);target.write_text('SYNTHETIC existing snapshot')
    with pytest.raises(ValueError):module.collect(days=1,root=tmp_path,interval=0)
    assert target.read_text()=='SYNTHETIC existing snapshot'
    with sqlite3.connect(tmp_path/'var/static-history.sqlite') as db:
        assert db.execute('SELECT status FROM run').fetchone()[0]=='failed'
