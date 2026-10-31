"""Completude do recorte e plano espacial; todas as coordenadas deste teste são sintéticas."""

import json
from pathlib import Path
import pytest
from shapely.geometry import Point, mapping, box
from shapely.ops import transform
from transporte.geo import MunicipalReferenceArea, PROJECT, UNPROJECT
from transporte.geo import assign_neighborhoods
from transporte.stop_inventory import grid_queries, build_inventory, refresh_inventory


def test_grid_covers_rectangle_with_queries_not_bus_locations():
    metric = box(480000, 6685000, 484000, 6688000)
    geographic = transform(UNPROJECT, metric)
    area = MunicipalReferenceArea(
        {
            "features": [
                {"geometry": mapping(geographic), "properties": {"BAIRRO": "SYNTHETIC"}}
            ]
        }
    )
    queries = grid_queries(area, 700)
    assert queries and all(area.point(p.x, p.y) for p in queries)
    points = [transform(PROJECT, p) for p in queries]
    assert len({(p.x, p.y) for p in points}) == len(points)
    # Raio observado da API é 500 m; grade de 700 m deve cobrir este caso convexo.
    for x in range(480000, 484001, 200):
        for y in range(6685000, 6688001, 200):
            assert min(Point(x, y).distance(p) for p in points) <= 500.1
    with pytest.raises(ValueError, match="Espaçamento"):
        grid_queries(area, 100)


def test_inventory_counts_unique_ids_and_distinguishes_missing_source_coordinates():
    links = {"11": {"1", "2"}, "12": {"1"}, "13": {"2"}}
    sources = {
        r: {
            "url": "https://SYNTHETIC.invalid/line",
            "sha256": "a" * 64,
            "fetched_at": "2026-10-31T10:00:00+00:00",
        }
        for r in ["1", "2"]
    }
    feature = {"properties": {"stop_id": "11"}}
    inventory = build_inventory(
        links,
        {},
        sources,
        [feature],
        {"12": "outside_reference_area"},
        "2026-10-31T11:00:00+00:00",
        3,
    )
    assert inventory["source_stop_ids"] == 3
    assert inventory["located_stop_ids"] == 1
    assert inventory["unlocated_stop_ids"] == 2
    assert inventory["localization_pct"] == 33.33
    assert inventory["status_counts"] == {
        "located": 1,
        "outside_reference_area": 1,
        "pending": 1,
    }
    assert sum(r["known_stop_ids"] for r in inventory["routes"]) == 4
    updated = refresh_inventory(inventory, [feature, {"properties": {"stop_id": "13"}}])
    assert updated["located_stop_ids"] == 2 and inventory["located_stop_ids"] == 1
    assert updated["routes"][1]["localization_pct"] == 100
    assert "coordinates" not in json.dumps(inventory["stops"])


def test_empty_list_does_not_report_a_zero_percent_network():
    inventory = build_inventory({}, {}, {}, [], {}, "2026-10-31T11:00:00+00:00", 81)
    assert inventory["localization_pct"] is None


def test_boundary_overlap_never_double_counts_stop_between_neighborhoods():
    polygons = [box(-51.2, -29.91, -51.18, -29.89), box(-51.19, -29.91, -51.17, -29.89)]
    points = [Point(-51.185, -29.9), Point(-51.16, -29.9), Point(-51.175, -29.9)]
    assigned, ambiguous = assign_neighborhoods(polygons, points)
    assert assigned == [0, None, 1] and ambiguous == 1
    assert sum(assigned.count(i) for i in range(2)) + assigned.count(None) == len(
        points
    )
