import base64
from datetime import datetime,timezone,timedelta
from fastapi.testclient import TestClient
import pytest
from transporte.store import Store
from transporte.audit import normalize_position
from backend.app import create_app

@pytest.fixture
def store(tmp_path):
    s=Store('sqlite:///'+str(tmp_path/'operational.sqlite'));s.initialize();return s

@pytest.fixture
def sample():
    return normalize_position({'source_id':'SYNTHETIC','vehicle_id':'SYNTHETIC-VEHICLE','route_id':'TEST',
        'observed_at':datetime.now(timezone.utc).isoformat(),'longitude':-51.18,'latitude':-29.92,
        'scope':'municipal','municipality_code':'4304606'})

def test_history_immutable_and_deduplicated(store,sample):
    assert store.insert([sample])==1 and store.insert([sample])==0
    changed=sample|{'longitude':-51.181}
    assert store.insert([changed])==1 and len(store.history())==2
    assert len(store.latest((datetime.now(timezone.utc)-timedelta(minutes=3)).isoformat()))==1

def test_no_private_data_without_auth(store,monkeypatch):
    monkeypatch.setenv('ADMIN_API_KEY','SYNTHETIC-TEST-KEY-'+'x'*32)
    c=TestClient(create_app(store))
    assert c.get('/internal/positions?start=2026-01-01&end=2026-01-02').status_code==401
    assert c.get('/admin').status_code==401
    assert c.get('/v1/health').status_code==200
    assert c.get('/v1/vehicles').json()['status']=='unavailable'

def test_admin_fail_closed_without_key(store,monkeypatch):
    monkeypatch.delenv('ADMIN_API_KEY',raising=False)
    c=TestClient(create_app(store));assert c.get('/admin').status_code==503

def test_authenticated_queries_and_exports(store,sample,monkeypatch):
    key='SYNTHETIC-KEY-'+'x'*32;monkeypatch.setenv('ADMIN_API_KEY',key)
    store.insert([sample]);c=TestClient(create_app(store));headers={'Authorization':'Bearer '+key}
    now=datetime.now(timezone.utc);query={'start':(now-timedelta(hours=1)).isoformat(),'end':(now+timedelta(hours=1)).isoformat()}
    r=c.get('/internal/positions',params=query,headers=headers)
    assert r.status_code==200 and len(r.json()['data'])==1
    assert c.get('/internal/export',params=query|{'format':'geojson'},headers=headers).json()['features'][0]['geometry']['type']=='Point'
    assert 'SYNTHETIC-VEHICLE' in c.get('/internal/export',params=query,headers=headers).text
    assert c.get('/internal/positions',params={'start':'2026-01-01','end':'2026-02-01'},headers=headers).status_code==422
    assert c.get('/internal/export',params=query|{'format':'exe'},headers=headers).status_code==422

def test_public_expiry_and_homologation(store,sample,monkeypatch):
    monkeypatch.setenv('SOURCE_HOMOLOGATED','true');monkeypatch.setenv('PUBLIC_POSITIONS_ENABLED','true');store.insert([sample]);c=TestClient(create_app(store))
    assert len(c.get('/v1/vehicles').json()['vehicles'])==1
    assert 'payload' not in c.get('/v1/vehicles').text

def test_event_history_and_review(store,monkeypatch):
    key='SYNTHETIC-KEY-'+'x'*32;monkeypatch.setenv('ADMIN_API_KEY',key)
    base={'source_id':'SYNTHETIC','vehicle_id':'TEST','route_id':'TEST','latitude':-29.92}
    values=[base|{'longitude':-51.18,'observed_at':'2026-01-01T00:00:00+00:00'},base|{'longitude':-51.1,'observed_at':'2026-01-01T00:00:10+00:00'}]
    store.save_events(values);store.save_events(values);events=store.events();assert len(events)==1
    c=TestClient(create_app(store));headers={'Authorization':'Basic '+base64.b64encode(('admin:'+key).encode()).decode()}
    assert c.get('/admin',headers=headers).status_code==200
    r=c.post('/internal/events/'+events[0]['id']+'/reviews',headers=headers,json={'classification':'inconclusive','reason':'SYNTHETIC: necessário verificar erro de GPS.'})
    assert r.status_code==200
    with store.connection() as conn:assert conn.execute('SELECT COUNT(*) FROM audit_review').fetchone()[0]==1

def test_reference_public_api_exposes_consultation_metadata(store,sample,monkeypatch):
    monkeypatch.setenv('PUBLIC_POSITIONS_ENABLED','true')
    monkeypatch.setenv('SOURCE_HOMOLOGATED','false')
    v=sample|{
        'fetched_at':sample['observed_at'],
        'time_basis':'client_fetch',
        'source_observed_at':None,
        'signal_status':'SC',
        'stale_polls':3,
        'bearing':None,
        'source_itinerary_id':'2457',
        'route_relation':'reference_not_homologated'
    }
    store.insert([v])
    c=TestClient(create_app(store))
    result=c.get('/v1/vehicles')
    assert result.status_code==200
    assert result.headers['Cache-Control']=='no-store'
    doc=result.json()
    assert doc['status']=='reference' and len(doc['vehicles'])==1
    row=doc['vehicles'][0]
    assert row['time_basis']=='client_fetch'
    assert row['signal_status']=='SC' and row['stale_polls']==3
    assert row['source_itinerary_id']=='2457'
    assert row['source_observed_at'] is None
    assert row['route_relation']=='reference_not_homologated'
    assert 'payload' not in result.text


def test_public_vehicle_api_has_rate_limit(store,monkeypatch):
    monkeypatch.delenv('SOURCE_HOMOLOGATED',raising=False)
    monkeypatch.delenv('PUBLIC_POSITIONS_ENABLED',raising=False)
    c=TestClient(create_app(store))
    assert all(c.get('/v1/vehicles').status_code==200 for _ in range(60))
    response=c.get('/v1/vehicles')
    assert response.status_code==429
    assert response.headers['Retry-After']=='60'


def test_source_homologation_never_bypasses_publication_opt_in(store,sample,monkeypatch):
    monkeypatch.setenv('SOURCE_HOMOLOGATED','true')
    monkeypatch.setenv('PUBLIC_POSITIONS_ENABLED','false')
    store.insert([sample])
    result=TestClient(create_app(store)).get('/v1/vehicles').json()
    assert result['status']=='unavailable'
    assert result['vehicles']==[] and result['generated_at'] is None


def test_unverified_client_fetch_never_claimed_as_gps_homologated(store,sample,monkeypatch):
    monkeypatch.setenv('SOURCE_HOMOLOGATED','true')
    monkeypatch.setenv('PUBLIC_POSITIONS_ENABLED','true')
    store.insert([sample | {
        'time_basis':'client_fetch',
        'fetched_at':sample['observed_at'],
        'source_observed_at':None,
        'route_relation':'reference_not_homologated'
    }])
    result=TestClient(create_app(store)).get('/v1/vehicles').json()
    assert result['status']=='reference'
    assert result['vehicles'][0]['time_basis']=='client_fetch'


def test_public_vehicle_rate_limit_is_configurable(store,monkeypatch):
    monkeypatch.setenv('PUBLIC_API_LIMIT_PER_MINUTE','2')
    app=create_app(store)
    client=TestClient(app)
    assert client.get('/v1/vehicles').status_code==200
    assert client.get('/v1/vehicles').status_code==200
    assert client.get('/v1/vehicles').status_code==429


def test_untrusted_forwarded_client_ip_cannot_bypass_limit(store,monkeypatch):
    monkeypatch.setenv('PUBLIC_API_LIMIT_PER_MINUTE','1')
    monkeypatch.delenv('TRUSTED_PROXY_CIDRS',raising=False)
    client=TestClient(create_app(store))
    assert client.get('/v1/vehicles',headers={'X-Real-IP':'203.0.113.2'}).status_code==200
    assert client.get('/v1/vehicles',headers={'X-Real-IP':'203.0.113.3'}).status_code==429



def test_empty_source_does_not_claim_live_availability(store,monkeypatch):
    monkeypatch.setenv('SOURCE_HOMOLOGATED','true')
    monkeypatch.setenv('PUBLIC_POSITIONS_ENABLED','true')
    result=TestClient(create_app(store)).get('/v1/vehicles').json()
    assert result['status']=='reference'
    assert result['vehicles']==[] and result['generated_at'] is None
