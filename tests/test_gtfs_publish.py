from __future__ import annotations
import zipfile
from pathlib import Path
import pytest
from scripts.publish_gtfs import audit, publish_geography
import json

FIXTURE = {
    "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\n1,Teste,https://example.invalid,America/Sao_Paulo\n",
    "routes.txt": "route_id,route_short_name,route_long_name,route_type\n10,05001,Linha Teste,3\n",
    "trips.txt": "route_id,service_id,trip_id,shape_id,direction_id\n10,1,T1,S1,0\n",
    "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nP1,Origem,-29.91,-51.19\n",
    "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,06:00:00,06:00:00,P1,1\n",
    "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nS1,-29.91,-51.19,1\n",
    "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n1,1,1,1,1,0,0,0,20261106,20270206\n",
}
def make_zip(path: Path, overrides:dict[str,str]|None=None):
    files={**FIXTURE,**(overrides or {})}
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items():z.writestr(name,content)

def test_audit_gtfs_zip(tmp_path:Path):
    path=tmp_path/"gtfs.zip"
    make_zip(path)
    result=audit(path)
    assert result["rows"]["routes"]==1
    assert result["rows"]["stop_times"]==1
    assert result["service_dates"]=={"start":"20261106","end":"20270206"}
    assert len(result["source_sha256"])==64

def test_rejects_wrong_stop_reference(tmp_path:Path):
    path=tmp_path/"gtfs.zip"
    make_zip(path,{"stop_times.txt":FIXTURE["stop_times.txt"].replace(",P1,1",",P9,1")})
    with pytest.raises(ValueError,match="stop_times"):
        audit(path)

def test_rejects_archive_path_traversal(tmp_path:Path):
    path=tmp_path/"gtfs.zip"
    make_zip(path)
    with zipfile.ZipFile(path,"a") as z:z.writestr("../invasao.txt","conteudo")
    with pytest.raises(ValueError,match="raiz"):
        audit(path)


def test_publish_geojson_preserves_gtfs_ids_and_crs(tmp_path: Path):
    path = tmp_path / "gtfs.zip"
    make_zip(path)
    output = tmp_path / "public"
    output.mkdir()
    summary = publish_geography(path, output)
    assert summary == {"stops": 1, "shapes": 1}
    stops = json.loads((output / "gtfs-paradas.geojson").read_text())
    shapes = json.loads((output / "gtfs-itinerarios.geojson").read_text())
    assert stops["type"] == "FeatureCollection"
    assert stops["features"][0]["geometry"]["coordinates"] == [-51.19, -29.91]
    assert stops["features"][0]["properties"]["gtfs_route_ids"] == ["10"]
    assert stops["features"][0]["properties"]["homologated"] is False
    assert shapes["features"][0]["geometry"]["coordinates"] == [[-51.19, -29.91]]
    assert shapes["features"][0]["properties"]["source"] == "GTFS Static"
