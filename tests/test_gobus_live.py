"""Regressão offline do adaptador GPS: nenhum GET sai para a TACOM."""
from datetime import datetime, timezone, timedelta
import json
import httpx
import pytest

from transporte.gobus import direction_info, vehicles, request_path
from transporte.gobus_live import LiveCollector, selected_stops, reference_shapes, private_path

def jsonp(callback, body):
    return callback + "(" + json.dumps(body, ensure_ascii=False) + ");"

INVENTORY = {
    "municipality_code":"4304606", "city_id":"4",
    "stops":[{"stop_id":"7844", "status":"located", "route_ids":["05000"]}]
}
SHAPES = {"type":"FeatureCollection","features":[
    {"type":"Feature", "properties":{
        "itinerary_id":"2457", "route_id":"05000", "source_route_code":"05000",
        "municipality_code":"4304606",
        "association_method":"city4_exact_code_and_prediction_itinerary",
        "homologated":False
    }}
]}
AREA={"type":"FeatureCollection","features":[{"type":"Feature","geometry":{
    "type":"Polygon","coordinates":[[
        [-51.25,-29.97],[-51.12,-29.97],[-51.12,-29.86],
        [-51.25,-29.86],[-51.25,-29.97]
    ]]}}]}
START=datetime(2026,10,31,15,0,tzinfo=timezone.utc)

def source(request, *, direction="2", vehicle_id="101", lon="-51,20", lat="-29,91"):
    assert request.method == "GET"
    assert request.url.host == "mpa.siumobile.com.br"
    assert request.url.port == 6060
    assert request.url.params.get("callback")
    if "buscarPrevisoes" in request.url.path:
        return httpx.Response(200,text=jsonp("retornoJSON",{
            "sucesso":True,"previsoes":[{"sgLin":"05000","codItinerario":2457,"numVeicGestor":"101"}]
        }))
    if "retornaVeiculosMapa" in request.url.path:
        return httpx.Response(200,text=jsonp("retornoJSONVeiculos",{
            "sucesso":True,"veiculos":[{"numVeicGestor":vehicle_id,
                "lat":lat,"long":lon,"direcao":direction}]
        }))
    raise AssertionError("Endpoint imprevisto")

def collector(now=START, transport=None, state=None, max_requests=6):
    client=httpx.Client(transport=transport or httpx.MockTransport(source))
    return LiveCollector(client,spacing=15,max_requests=max_requests,retries=0,
        clock=lambda:now,monotonic=lambda:0,sleep=lambda _:None,jitter=lambda:0,state=state)

@pytest.mark.parametrize("direction,bearing,status", [
    ("0",0,"ok"),("1",45,"ok"),("4",180,"ok"),("7",315,"ok"),
    (0,0,"ok"),("SC",None,"SC"),("SG",None,"SG"),(None,None,"ok")
])
def test_octants_are_not_degrees(direction,bearing,status):
    assert direction_info(direction)==(bearing,status)

def test_unsupported_octant_fails():
    with pytest.raises(ValueError):
        direction_info("360")

def test_single_vehicle_and_unusable_signal():
    data=jsonp("retornoJSONVeiculos",{"sucesso":True,"veiculo":{
        "numVeicGestor":"101","long":"-51,20","lat":"-29,91","direcao":"SC","sequencia":"9"}})
    row=vehicles(data)[0]
    assert row["longitude"]==-51.2
    assert row["latitude"]==-29.91
    assert row["signal_status"]=="SC" and row["bearing"] is None
    assert row["stop_sequence"]=="9"
    missing=jsonp("retornoJSONVeiculos",{"sucesso":True,"veiculo":{
        "numVeicGestor":"101","direcao":"SG"}})
    assert vehicles(missing)[0]["longitude"] is None

def test_only_real_active_pairs_become_reference_positions():
    c=collector()
    result=c.once(INVENTORY,SHAPES,AREA,stop_queries=1,itinerary_queries=1)
    assert result["status"]=="reference"
    assert result["diagnostics"]["requests"]==2
    p=result["vehicles"][0]
    assert p["route_id"]=="05000" and p["source_itinerary_id"]=="2457"
    assert p["time_basis"]=="client_fetch" and p["source_observed_at"] is None
    assert p["bearing"]==90 and p["stale_polls"]==0
    assert p["route_relation"]=="reference_not_homologated"
    assert p["signal_status"]=="ok"
    c2=collector(START+timedelta(seconds=60),state=c.state)
    again=c2.once(INVENTORY,SHAPES,AREA,stop_queries=1,itinerary_queries=1)
    assert again["vehicles"][0]["stale_polls"]==1

def test_no_vehicle_without_prediction_pair():
    fake=httpx.MockTransport(lambda request:source(request,vehicle_id="999"))
    c=collector(transport=fake)
    assert c.once(INVENTORY,SHAPES,AREA,stop_queries=1,itinerary_queries=1)["vehicles"]==[]

def test_no_foreign_coordinate():
    fake=httpx.MockTransport(lambda request:source(request,lon="-51,55",lat="-29,91"))
    assert collector(transport=fake).once(INVENTORY,SHAPES,AREA,stop_queries=1,itinerary_queries=1)["vehicles"]==[]

def test_only_reference_itineraries_and_municipal_stops():
    assert reference_shapes(SHAPES)=={"2457":("05000","5000")}
    assert selected_stops(INVENTORY,{"05000"},0,5)==["7844"]
    assert selected_stops(INVENTORY,{"05100"},0,5)==[]
    with pytest.raises(ValueError):
        selected_stops(INVENTORY|{"city_id":"5"},{"05000"},0,5)

def test_request_budget_enforced_without_guessing():
    result=collector(max_requests=1).once(INVENTORY,SHAPES,AREA,stop_queries=1,itinerary_queries=1)
    assert result["vehicles"]==[] and result["diagnostics"]["requests"]==1

def test_403_suspends_access():
    fake=httpx.MockTransport(lambda request:httpx.Response(403,text="SYNTHETIC-SECRET"))
    c=collector(transport=fake)
    result=c.once(INVENTORY,SHAPES,AREA,stop_queries=1,itinerary_queries=1)
    assert c.denied and result["vehicles"]==[] and result["diagnostics"]["requests"]==1
    assert "SYNTHETIC" not in str(result)

def test_cache_does_not_create_fake_new_observation():
    c=collector()
    one,t1=c.get("previsoes",parada="7844",acessivel="false",cidade="MPA")
    two,t2=c.get("previsoes",parada="7844",acessivel="false",cidade="MPA")
    assert one==two and t1==t2 and c.requests==1 and c.cache_hits==1

def test_private_paths_only(tmp_path):
    accepted=private_path(tmp_path,tmp_path/"var/gobus/live-feed.json")
    assert accepted.name=="live-feed.json"
    with pytest.raises(ValueError):
        private_path(tmp_path,tmp_path/"public/data/vehicles.json")
