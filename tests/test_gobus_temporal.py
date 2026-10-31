"""Qualidade temporal: horário de consulta nunca é tratado como timestamp GPS."""
from datetime import datetime, timezone, timedelta
import pytest
from transporte.audit import normalize_position, trajectory_events, VERSION

T=datetime(2026,10,31,15,0,tzinfo=timezone.utc)
def base(**kwargs):
    row={
        "source_id":"SYNTHETIC", "vehicle_id":"101", "route_id":"05000",
        "scope":"municipal","municipality_code":"4304606",
        "longitude":-51.20,"latitude":-29.91,
        "observed_at":T.isoformat(),"fetched_at":T.isoformat(),
        "source_observed_at":None,
        "time_basis":"client_fetch","signal_status":"ok","stale_polls":0,
        "route_relation":"reference_not_homologated",
        "bearing":180,"bearing_basis":"apk_octant_north_unverified",
        "speed_kmh":None
    }
    return row|kwargs

def test_preserve_client_fetch_and_signal():
    p=normalize_position(base(signal_status="SG",bearing=None,stale_polls=7),now=T)
    assert p["observed_at"]==p["fetched_at"]
    assert p["time_basis"]=="client_fetch" and p["source_observed_at"] is None
    assert p["signal_status"]=="SG" and p["stale_polls"]==7
    assert p["bearing"] is None and p["route_relation"]=="reference_not_homologated"

@pytest.mark.parametrize("bad",[
    {"speed_kmh":32},
    {"time_basis":"unknown"},
    {"stale_polls":-1},
    {"stale_polls":True},
    {"signal_status":"OFFLINE"},
    {"signal_status":"SC","bearing":45},
    {"fetched_at":(T-timedelta(minutes=3)).isoformat()},
])
def test_reject_unsafe_client_fetch_attributes(bad):
    with pytest.raises(ValueError):
        normalize_position(base(**bad),now=T)

def test_client_fetch_does_not_establish_deviation_or_speed():
    first=normalize_position(base(longitude=-51.20),now=T+timedelta(minutes=2))
    second=normalize_position(base(
        longitude=-51.19,observed_at=(T+timedelta(seconds=60)).isoformat(),
        fetched_at=(T+timedelta(seconds=60)).isoformat(),
    ),now=T+timedelta(minutes=2))
    events=trajectory_events([first,second],
        authorized_shape=[[-51.15,-29.91],[-51.15,-29.90]])
    assert any(x["kind"]=="possible_deviation" and x["classification"]=="inconclusive" for x in events)
    for event in events:
        assert event["classification"]=="inconclusive"
        assert event["is_infraction"] is False and event["algorithm_version"]==VERSION
