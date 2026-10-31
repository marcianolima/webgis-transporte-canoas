"""Integração offline collector -> store -> API. Somente dados sintéticos."""
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from backend.app import create_app
from transporte.gobus_live_worker import ingest
from transporte.store import Store


class SyntheticCollector:
    def __init__(self, positions):
        self.positions=positions
    def once(self, *_):
        return {"status":"reference","vehicles":self.positions,
                "diagnostics":{"requests":2,"sampled_stops":1,
                               "vehicle_id":"PRIVATE-DO-NOT-EXPOSE"}}


def position():
    now=datetime.now(timezone.utc).isoformat()
    return {
        "source_id":"SYNTHETIC-GOBUS","vehicle_id":"101",
        "route_id":"05000","source_itinerary_id":"2457",
        "route_relation":"reference_not_homologated",
        "scope":"municipal","municipality_code":"4304606",
        "longitude":-51.20,"latitude":-29.91,
        "observed_at":now,"fetched_at":now,
        "source_observed_at":None,"time_basis":"client_fetch",
        "signal_status":"SG","bearing":None,
        "bearing_basis":None,"speed_kmh":None,"stale_polls":2
    }


def test_private_worker_to_public_reference_api(tmp_path,monkeypatch):
    store=Store('sqlite:///'+str(tmp_path/'gobus.sqlite'));store.initialize()
    run,report=ingest(store,SyntheticCollector([position()]),{},{},{})
    assert run["status"]=="reference" and run["accepted"]==1
    assert report["vehicles"][0]["signal_status"]=="SG"
    history=store.history()
    assert len(history)==1 and history[0]["time_basis"]=="client_fetch"
    monkeypatch.setenv("PUBLIC_POSITIONS_ENABLED","true")
    monkeypatch.setenv("SOURCE_HOMOLOGATED","false")
    response=TestClient(create_app(store)).get("/v1/vehicles")
    assert response.status_code==200
    data=response.json()
    assert data["status"]=="reference"
    assert data["vehicles"][0]["signal_status"]=="SG"
    assert data["vehicles"][0]["stale_polls"]==2
    assert "timestamp GPS" in data["message"]
    health=TestClient(create_app(store)).get("/v1/health").json()
    assert health["accepted_last_run"]==1
    assert health["source_diagnostics"]["requests"]==2
    assert "PRIVATE-DO-NOT-EXPOSE" not in str(health)


def test_worker_rejects_fake_municipal_scope(tmp_path):
    store=Store('sqlite:///'+str(tmp_path/'gobus.sqlite'));store.initialize()
    bad=position()|{"municipality_code":"9999999"}
    run,report=ingest(store,SyntheticCollector([bad]),{},{},{})
    assert run["status"]=="partial" and run["rejected"]==1
    assert report["vehicles"]==[bad]
    assert store.history()==[]
