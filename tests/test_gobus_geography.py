"""Contratos sintéticos isolados e regressão territorial com a base real."""

import json
from pathlib import Path
import pytest
from transporte.gobus import request_path
from transporte.gobus_geography import collect, LocalArea
from transporte.geo import valid_coordinate
from transporte.import_stops import validate_stops

ROOT = Path(__file__).resolve().parents[1]


def test_viamao_passes_envelope_but_fails_municipal_polygon():
    area = LocalArea(
        json.loads((ROOT / "public/data/bairros-oficiais.geojson").read_text())
    )
    assert valid_coordinate(
        -51.095066, -30.051145
    )  # Regressão da antiga validação larga.
    assert not area.point(-51.095066, -30.051145)
    assert area.point(-51.23941, -29.904643)
    assert (
        request_path("parada_detalhes", parada="8746")
        == "buscarDadosParada/8746/0/retornoJSONPontosItinerario"
    )


def test_importer_rejects_viamao_even_with_canoas_route_id():
    with pytest.raises(ValueError, match="Canoas"):
        validate_stops(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [-51.095066, -30.051145],
                        },
                        "properties": {"stop_id": "SYNTHETIC", "route_ids": ["05000"]},
                    }
                ],
            },
            {"routes": [{"id": "05000"}]},
        )


class FakeReader:
    count = 0

    def __init__(self, outside=False):
        self.outside = outside
        self.calls = []

    def get(self, kind, **params):
        self.count += 1
        self.calls.append(kind)
        if kind == "cidades_linhas":
            doc = {"cidade": [{"cod": "4", "desc": "CANOAS"}]}
        elif kind == "linhas":
            doc = {
                "linhas": [
                    {
                        "cod": "5000",
                        "sgl": "05000",
                        "nom": "SYNTHETIC",
                        "praca": "MPA",
                        "codcid": "4",
                    },
                    {
                        "cod": "9",
                        "sgl": "9",
                        "nom": "SYNTHETIC METRO",
                        "praca": "MPA",
                        "codcid": "14",
                    },
                ]
            }
        elif kind == "paradas_linha":
            doc = {
                "paradas": [
                    {"cod": 11, "end": "SYNTHETIC A", "sent": "SYNTHETIC"},
                    {"cod": 12, "end": "SYNTHETIC B"},
                ]
            }
        elif kind == "paradas_proximas":
            doc = {
                "paradas": [
                    {"cod": 11, "x": -51.19, "y": -29.90, "desc": "SYNTHETIC A"},
                    {"cod": 12, "x": -51.095, "y": -30.05, "desc": "SYNTHETIC FORA"},
                ]
            }
        elif kind == "parada_detalhes":
            doc = {
                "paradas": [
                    {"cod": 12, "x": -51.095, "y": -30.05, "desc": "SYNTHETIC FORA"}
                ]
            }
        elif kind == "previsoes":
            doc = {
                "previsoes": [
                    {
                        "sgLin": "05000",
                        "codItinerario": 123,
                        "numVeicGestor": "SYNTHETIC-NAO-PUBLICAR",
                    },
                    {"sgLin": "9", "codItinerario": 999},
                ]
            }
        elif kind == "itinerario":
            doc = {
                "itinerarios": (
                    [
                        {"coordX": -51.19, "coordY": -29.90},
                        {"coordX": -51.18, "coordY": -29.90},
                    ]
                    if not self.outside
                    else [
                        {"coordX": -51.1, "coordY": -30.05},
                        {"coordX": -51.09, "coordY": -30.04},
                    ]
                )
            }
        else:
            raise AssertionError(kind)
        return {"sucesso": True, **doc}, {
            "url": "http://mpa.siumobile.com.br:6060/SYNTHETIC/" + kind,
            "fetched_at": "2026-10-31T10:00:00+00:00",
            "sha256": "a" * 64,
        }


def fixture(root):
    data = root / "public/data"
    data.mkdir(parents=True)
    area = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"BAIRRO": "SYNTHETIC"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-51.21, -29.92],
                            [-51.16, -29.92],
                            [-51.16, -29.88],
                            [-51.21, -29.88],
                            [-51.21, -29.92],
                        ]
                    ],
                },
            }
        ],
    }
    (data / "bairros-oficiais.geojson").write_text(json.dumps(area))
    area["features"][0]["properties"]["pop"] = 100
    (data / "censo2022-setores.geojson").write_text(json.dumps(area))
    (data / "network.json").write_text(
        json.dumps(
            {
                "routes": [
                    {
                        "id": "05000",
                        "code": "5000",
                        "name": "SYNTHETIC",
                        "dates": ["2026-10-31"],
                    }
                ]
            }
        )
    )
    return data


def test_collect_uses_observed_itinerary_and_excludes_foreign_points(tmp_path):
    fixture(tmp_path)
    reader = FakeReader()
    result = collect(
        tmp_path,
        reader=reader,
        service_date="2026-10-31",
        geo_samples=1,
        prediction_samples=1,
    )
    assert result["published_stops"] == 1 and result["published_itineraries"] == 1
    out = tmp_path / "var/gobus/geography"
    stops = json.loads((out / "stops.geojson").read_text())
    routes = json.loads((out / "route-shapes.geojson").read_text())
    assert stops["features"][0]["properties"]["stop_id"] == "11"
    assert routes["features"][0]["properties"]["shape_id"] == "SIU-123"
    assert routes["features"][0]["properties"]["homologated"] is False
    assert "paradas_geograficas" not in reader.calls and "veiculos" not in reader.calls
    assert "numVeicGestor" not in (out / "route-shapes.geojson").read_text()


def test_bad_shape_is_quarantined_without_connecting_stops(tmp_path):
    fixture(tmp_path)
    result = collect(
        tmp_path, reader=FakeReader(outside=True), geo_samples=1, prediction_samples=1
    )
    assert result["published_itineraries"] == 0 and result["published_stops"] == 1
    assert len(result["rejected_shapes"]) == 1


def test_publication_preserves_itinerary_missing_from_next_sample(
    tmp_path, monkeypatch
):
    from transporte import publish_geography as publication

    fixture(tmp_path)
    collect(
        tmp_path,
        reader=FakeReader(),
        service_date="2026-10-31",
        geo_samples=1,
        prediction_samples=1,
    )
    monkeypatch.setattr(publication, "prepare", lambda _: None)
    monkeypatch.setattr(publication, "build_pmtiles", lambda _: None)
    publication.publish(tmp_path)
    active = tmp_path / "public/data/route-shapes.geojson"
    before = json.loads(active.read_text())["features"][0]
    current = tmp_path / "var/gobus/geography/route-shapes.geojson"
    document = json.loads(current.read_text())
    document["features"] = []
    current.write_text(json.dumps(document))
    result = publication.publish(tmp_path)
    after = json.loads(active.read_text())["features"][0]
    assert before == after and result["published_itineraries"] == 1
    stops = tmp_path / "var/gobus/geography/stops.geojson"
    document = json.loads(stops.read_text())
    document["features"] = []
    stops.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="vazia"):
        publication.publish(tmp_path)
    assert before == json.loads(active.read_text())["features"][0]
