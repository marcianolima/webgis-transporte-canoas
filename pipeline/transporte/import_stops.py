"""Importação aprovada de paradas geográficas TACOM/GoBus para o WebGIS.

Executar APENAS após revisão de município, códigos e direito de publicação.
A rotina não consulta a TACOM. Backups por hash em var/stop-history.
"""

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from .collect import dump
from .geo import valid_coordinate, MunicipalReferenceArea
from .http import utcnow

MUNICIPALITY = "4304606"


def validate_stops(document: dict, network: dict) -> list[dict]:
    if document.get("type") != "FeatureCollection" or document.get("crs"):
        raise ValueError("Esperado GeoJSON FeatureCollection EPSG:4326")
    area = MunicipalReferenceArea(
        json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "public/data/bairros-oficiais.geojson"
            ).read_text()
        )
    )
    allowed = {str(r["id"]) for r in network.get("routes", [])}
    seen = {}
    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("Nenhuma parada para importar")
    for feature in features:
        geometry = feature.get("geometry") or {}
        if (
            geometry.get("type") != "Point"
            or not isinstance(geometry.get("coordinates"), list)
            or len(geometry["coordinates"]) != 2
        ):
            raise ValueError("Parada precisa ser Point com lon/lat")
        lon, lat = geometry["coordinates"]
        if not valid_coordinate(lon, lat) or not area.point(lon, lat):
            raise ValueError("Parada fora do envelope operacional de Canoas")
        p = feature.get("properties") or {}
        sid = str(p.get("stop_id") or "")
        if not sid or len(sid) > 64:
            raise ValueError("Identificador de parada inválido")
        routes = p.get("route_ids")
        if not isinstance(routes, list) or not routes:
            raise ValueError("Parada sem linhas vinculadas")
        route_ids = sorted(set(map(str, routes)))
        if not set(route_ids).issubset(allowed):
            raise ValueError("Parada associada à linha desconhecida")
        if sid in seen:
            raise ValueError("Parada repetida: " + sid)
        seen[sid] = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {
                "stop_id": sid,
                "name": str(p.get("name") or ""),
                "siu": str(p.get("siu") or ""),
                "route_ids": route_ids,
                "route_ids_csv": ",".join(route_ids),
                "municipality_code": MUNICIPALITY,
                "source": "TACOM-GoBus",
            },
        }
    return [seen[k] for k in sorted(seen)]


def import_stops(
    root,
    input_path,
    *,
    source_url,
    source_name,
    reference_date,
    municipality_code,
    approved=False,
):
    if approved is not True:
        raise ValueError("Publicação de paradas exige aprovação explícita")
    if municipality_code != MUNICIPALITY:
        raise ValueError("Somente Canoas/4304606")
    parsed = urlparse(source_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Exige origem HTTPS auditável e sem credenciais")
    if not source_name.strip():
        raise ValueError("Fonte não identificada")
    date.fromisoformat(reference_date)
    root = Path(root)
    source = Path(input_path)
    if source.stat().st_size > 20_000_000:
        raise ValueError("Arquivo acima do limite de 20MB")
    content = source.read_bytes()
    network = json.loads((root / "public/data/network.json").read_text())
    features = validate_stops(json.loads(content), network)
    now = utcnow()
    digest = hashlib.sha256(content).hexdigest()
    for f in features:
        f["properties"].update(
            {
                "status": "reference",
                "source_name": source_name,
                "source_url": source_url,
                "source_sha256": digest,
                "reference_date": reference_date,
                "fetched_at": now,
            }
        )
    final = {
        "type": "FeatureCollection",
        "features": features,
        "status": "reference",
        "generated_at": now,
        "description": "Cadastro de paradas para referência, sujeito a validade e homologação municipal.",
    }
    folder = root / "var/stop-history"
    folder.mkdir(parents=True, exist_ok=True)
    active = root / "public/data/stops.geojson"
    for blob, ext in [
        (content, ".source.geojson"),
        (active.read_bytes() if active.exists() else b"", ".previous.geojson"),
    ]:
        if blob:
            target = folder / (hashlib.sha256(blob).hexdigest() + ext)
            if not target.exists():
                target.write_bytes(blob)
    dump(active, final)
    return final


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    for key in ("source-url", "source-name", "reference-date", "municipality-code"):
        p.add_argument("--" + key, required=True)
    p.add_argument(
        "--approved",
        action="store_true",
        help="Aprovo publicação após revisão de fonte, códigos e município",
    )
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = p.parse_args()
    result = import_stops(
        args.root,
        args.input,
        source_url=args.source_url,
        source_name=args.source_name,
        reference_date=args.reference_date,
        municipality_code=args.municipality_code,
        approved=args.approved,
    )
    from .geo import prepare
    from .tiles import build_pmtiles

    prepare(args.root)
    build_pmtiles(args.root)
    print(
        json.dumps(
            {"event": "stops_imported", "count": len(result["features"])},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
