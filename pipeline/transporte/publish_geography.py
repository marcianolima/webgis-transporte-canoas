"""Publica produtos geográficos normalizados de referência, preservando versões.

Não promove dados a homologados. Não publica JSONP, previsões ou IDs de veículos.
"""

import argparse
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import uuid
from .collect import dump
from .geo import MunicipalReferenceArea, prepare
from .http import utcnow
from .persistence import atomic_bytes, atomic_json
from .tiles import build_pmtiles


def merge_features(previous, incoming, key):
    """Ausência em amostra não é remoção; conflitos de identidade suspendem publicação."""
    merged = {str(f["properties"][key]): copy.deepcopy(f) for f in previous}
    for feature in incoming:
        feature = copy.deepcopy(feature)
        p = feature["properties"]
        identity = str(p[key])
        old = merged.get(identity)
        if old:
            old_p = old["properties"]
            if key == "shape_id" and old_p["route_id"] != p["route_id"]:
                raise ValueError("Itinerário com associação conflitante: " + identity)
            if key == "stop_id":
                # Mudança de coordenada é preservada na captura privada, mas exige revisão.
                if old["geometry"] != feature["geometry"]:
                    raise ValueError("Parada com coordenada alterada: " + identity)
                p["route_ids"] = sorted(set(old_p["route_ids"]) | set(p["route_ids"]))
                p["route_ids_csv"] = ",".join(p["route_ids"])
                directions = copy.deepcopy(old_p.get("directions_by_route", {}))
                for route, values in p.get("directions_by_route", {}).items():
                    directions[route] = sorted(
                        set(directions.get(route, [])) | set(values)
                    )
                p["directions_by_route"] = directions
            if old_p.get("fetched_at", "") > p.get("fetched_at", ""):
                # Um cache antigo não substitui uma observação mais recente.
                newer = copy.deepcopy(old)
                if key == "stop_id":
                    for field in ("route_ids", "route_ids_csv", "directions_by_route"):
                        newer["properties"][field] = p[field]
                feature = newer
        merged[identity] = feature
    return [merged[k] for k in sorted(merged)]


def _prepare(root, source, archive):
    root = Path(root)
    public = root / "public/data"
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
    if any(
        document.get("generated_at") != summary.get("generated_at")
        for document in (routes, stops)
    ):
        raise ValueError("Captura incompleta: datas dos produtos não coincidem")
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
        document["features"] = merge_features(
            previous.get("features", []), document["features"], key
        )
        for content, label in [
            (target.read_bytes() if target.exists() else b"", "previous"),
            (json.dumps(document, ensure_ascii=False).encode(), "normalized"),
        ]:
            if content:
                path = archive / (
                    hashlib.sha256(content).hexdigest() + "." + label + ".geojson"
                )
                if not path.exists():
                    atomic_bytes(path, content)
        dump(target, document)
    previous_summary_path = public / "transport-geography.json"
    previous_summary = (
        json.loads(previous_summary_path.read_text())
        if previous_summary_path.exists()
        else {}
    )
    summary["line_stop_sources"] = {
        **previous_summary.get("line_stop_sources", {}),
        **summary.get("line_stop_sources", {}),
    }
    present = {f["properties"]["route_id"] for f in routes["features"]}
    summary.update(
        {
            "published_stops": len(stops["features"]),
            "published_itineraries": len(routes["features"]),
            "routes_with_geometry": len(present),
            "missing_geometry_route_ids": sorted(allowed - present),
            "border_review_itineraries": sum(
                f["properties"].get("territorial_quality") == "border_review"
                for f in routes["features"]
            ),
            "publication_status": "partial_reference_not_homologated",
            "incremental_policy": "Ausência na amostra não remove geometrias anteriores; fetched_at preservado em cada feição.",
        }
    )
    dump(public / "transport-geography.json", summary)
    prepare(root)
    build_pmtiles(root)
    return summary


def _publish_locked(root):
    public = root / "public/data"
    private = root / "var/gobus"
    # Todos os cálculos e o PMTiles são concluídos em cópia isolada primeiro.
    with tempfile.TemporaryDirectory(prefix="publication-", dir=private) as temporary:
        stage = Path(temporary)
        staged_public = stage / "public/data"
        shutil.copytree(public, staged_public)
        result = _prepare(stage, private / "geography", private / "published-history")
        candidates = {
            p.relative_to(staged_public): p.read_bytes()
            for p in staged_public.rglob("*")
            if p.is_file()
        }
        changed = {
            name: data
            for name, data in candidates.items()
            if not (public / name).exists() or (public / name).read_bytes() != data
        }
        before = {
            name: (public / name).read_bytes() if (public / name).exists() else None
            for name in changed
        }
        run = (
            private
            / "publication-runs"
            / (utcnow().replace(":", "-") + "-" + uuid.uuid4().hex[:8])
        )
        run.mkdir(parents=True)
        for name, data in before.items():
            if data is not None:
                atomic_bytes(run / "before" / name, data)
        journal = {
            "created_at": utcnow(),
            "status": "prepared",
            "files": [
                {
                    "path": str(name),
                    "existed_before": before[name] is not None,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for name, data in changed.items()
            ],
        }
        atomic_json(run / "journal.json", journal)
        promoted = []
        try:
            for name, data in changed.items():
                atomic_bytes(public / name, data)
                promoted.append(name)
        except BaseException:
            for name in reversed(promoted):
                if before[name] is None:
                    (public / name).unlink(missing_ok=True)
                else:
                    atomic_bytes(public / name, before[name])
            journal["status"] = "rolled_back"
            atomic_json(run / "journal.json", journal)
            raise
        journal["status"] = "committed"
        atomic_json(run / "journal.json", journal)
        return result


def publish(root):
    root = Path(root).resolve()
    private = root / "var/gobus"
    private.mkdir(parents=True, exist_ok=True)
    with (private / "publication.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _publish_locked(root)


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
