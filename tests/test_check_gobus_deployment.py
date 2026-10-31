"""Aceite de implantação: somente duas leituras HTTP sintéticas."""
from datetime import datetime, timezone, timedelta
import httpx
import pytest
from scripts.check_gobus_deployment import approved_base, check

NOW=datetime(2026,10,31,16,0,tzinfo=timezone.utc)

def api_response(request, *,status="reference",delta=30,time_basis="client_fetch"):
    assert request.method=="GET"
    if request.url.path=="/v1/health":
        return httpx.Response(200,json={"status":"reference"})
    if request.url.path=="/v1/vehicles":
        t=(NOW-timedelta(seconds=delta)).isoformat()
        return httpx.Response(200,json={
            "status":status,"vehicles":[{
                "source_id":"SYNTHETIC","vehicle_id":"PRIVATE-FIXTURE",
                "route_id":"05000","longitude":-51.2,"latitude":-29.91,
                "observed_at":t,"fetched_at":t,
                "source_observed_at":None,"signal_status":"ok",
                "bearing":90,"speed_kmh":None,"time_basis":time_basis
            }]
        })
    raise AssertionError("Endpoint não permitido")

def test_acceptance_summary_redacts_ids_and_coordinates():
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        return api_response(request)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=check("https://api.example.test",client=client,clock=lambda:NOW)
    assert calls==["/v1/health","/v1/vehicles"]
    assert result["valid"] and result["vehicles_in_snapshot"]==1
    assert result["time_bases"]=={"client_fetch":1}
    assert "PRIVATE-FIXTURE" not in str(result)
    assert "-51.2" not in str(result)

def test_stale_consultation_fails():
    def handler(request):return api_response(request,delta=190)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=check("https://api.example.test",client=client,clock=lambda:NOW)
    assert result["validation_errors"]["expired_or_future"]==1
    assert not result["valid"]

def test_available_cannot_hide_client_fetch():
    def handler(request):return api_response(request,status="available")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=check("https://api.example.test",client=client,clock=lambda:NOW)
    assert result["validation_errors"]["unhomologated_position_as_available"]==1

@pytest.mark.parametrize("url",[
    "http://public.example.com","http://api.example.test",
    "https://user:pass@api.example.test","https://api.example.test/v1/vehicles",
    "https://api.example.test?token=abc","ftp://api.example.test"
])
def test_reject_unsafe_api_url(url):
    with pytest.raises(ValueError):
        approved_base(url)

def test_loopback_http_requires_opt_in():
    with pytest.raises(ValueError):
        approved_base("http://127.0.0.1:8000")
    assert approved_base("http://127.0.0.1:8000",True)=="http://127.0.0.1:8000"
