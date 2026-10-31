"""Publica produtos geográficos normalizados de referência, preservando versões.

Não promove dados a homologados. Não publica JSONP, previsões ou IDs de veículos.
"""

import argparse
import hashlib
import json
from pathlib import Path
from .collect import dump
from .geo import MunicipalReferenceArea, prepare
from .tiles import build_pmtiles


def publish(root):
    root = Path(root)
    public = root / "public/data"
    source = root / "var/gobus/geography"
    archive = root / "var/gobus/published-history"
    archive.mkdir(parents=True, exist_ok=True)
    area = MunicipalReferenceArea(
        json.loads((public / "bairros-oficiais.geojson").read_text())
    )
    allowed = {
        r["id"] for r in json.loads((public / "network.json").read_text())["routes"]
    }
    routes = json.loads((source / "route-shapes.geojson").read_text())
    stops = json.loads((source / "stops.geojson").read_text())
    summary = json.loads((source / "transport-geography.json").read_text())
    if summary.get("municipality_code") != "4304606" or summary.get("city_id") != "4":
        raise ValueError("Município não verificado")
    if not routes["features"] and not stops["features"]:
        raise ValueError("Captura vazia: preservar publicação anterior")
    for f in routes["features"]:
        p = f["properties"]
        quality = area.line(f)
        if (
            p.get("route_id") not in allowed
            or p.get("homologated") is not False
            or p.get("status") != "reference"
        ):
            raise ValueError("Percurso sem estado de referência ou linha conhecida")
        if (
            quality["local_length_pct"] < 80
            or quality["max_boundary_distance_m"] > 1500
        ):
            raise ValueError("Percurso incompatível com Canoas")
        if not p.get("prediction_evidence_sha256") or not p.get("source_sha256"):
            raise ValueError("Percurso sem evidência de associação")
    for f in stops["features"]:
        p = f["properties"]
        if (
            not p.get("route_ids")
            or not set(p["route_ids"]).issubset(allowed)
            or not area.point(*f["geometry"]["coordinates"])
        ):
            raise ValueError("Parada sem vínculo ou fora da área de referência")
    # Uma amostra de previsões não indica remoção dos itinerários ausentes na próxima captura.
    for name, document, key in [
        ("route-shapes.geojson", routes, "shape_id"),
        ("stops.geojson", stops, "stop_id"),
    ]:
        target = public / name
        previous = (
            json.loads(target.read_text()) if target.exists() else {"features": []}
        )
        merged = {
            str(f["properties"][key]): f
            for f in previous.get("features", [])
            if key in f.get("properties", {})
        }
        for f in document["features"]:
            merged[str(f["properties"][key])] = f
        document["features"] = [merged[k] for k in sorted(merged)]
        for content, label in [
            (target.read_bytes() if target.exists() else b"", "previous"),
            (json.dumps(document, ensure_ascii=False).encode(), "normalized"),
        ]:
            if content:
                path = archive / (
                    hashlib.sha256(content).hexdigest() + "." + label + ".geojson"
                )
                if not path.exists():
                    path.write_bytes(content)
        dump(target, document)
    summary.update(
        {
            "published_stops": len(stops["features"]),
            "published_itineraries": len(routes["features"]),
            "routes_with_geometry": len(
                {f["properties"]["route_id"] for f in routes["features"]}
            ),
            "publication_status": "partial_reference_not_homologated",
            "incremental_policy": "Ausência na amostra não remove geometrias anteriores; fetched_at preservado em cada feição.",
        }
    )
    dump(public / "transport-geography.json", summary)
    prepare(root)
    build_pmtiles(root)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = p.parse_args()
    r = publish(args.root)
    print(
        json.dumps(
            {
                k: r[k]
                for k in [
                    "published_stops",
                    "published_itineraries",
                    "routes_with_geometry",
                    "publication_status",
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
