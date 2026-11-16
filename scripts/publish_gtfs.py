#!/usr/bin/env python3
"""Valida e publica um pacote GTFS Static sem alterar as bases Sogal/TACOM.

Uso: python scripts/publish_gtfs.py inputs/gtfs-canoas.zip
O ZIP original é copiado sem transformação para public/data/gtfs-canoas.zip.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {"agency.txt", "routes.txt", "trips.txt", "stops.txt", "stop_times.txt", "shapes.txt", "calendar.txt"}
MAX_ZIP_BYTES = 35_000_000
MAX_DECOMPRESSED = 50_000_000


def rows(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with archive.open(name) as handle:
        return list(csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")))


def audit(source: Path) -> dict:
    if not source.is_file() or source.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("Pacote GTFS inexistente ou excessivamente grande")
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        failed_crc = archive.testzip()
        if failed_crc is not None:
            raise ValueError(f"Falha de CRC no arquivo GTFS: {failed_crc}")
        if len(names) != len(set(names)):
            raise ValueError("Nomes ZIP duplicados")
        if any("/" in n or "\\" in n or n.startswith(".") for n in names):
            raise ValueError("O pacote deve conter arquivos GTFS diretamente na raiz")
        if not REQUIRED.issubset(names):
            raise ValueError(f"GTFS incompleto: {sorted(REQUIRED-set(names))}")
        if sum(f.file_size for f in archive.infolist()) > MAX_DECOMPRESSED:
            raise ValueError("Conteúdo descomprimido excede limite de segurança")
        routes = rows(archive, "routes.txt")
        trips = rows(archive, "trips.txt")
        stops = rows(archive, "stops.txt")
        times = rows(archive, "stop_times.txt")
        shapes = rows(archive, "shapes.txt")
        calendars = rows(archive, "calendar.txt")
        route_ids = {r["route_id"] for r in routes}
        stop_ids = {r["stop_id"] for r in stops}
        trip_ids = {r["trip_id"] for r in trips}
        shape_ids = {r["shape_id"] for r in shapes}
        service_ids = {r["service_id"] for r in calendars}
        if len(route_ids) != len(routes) or len(stop_ids) != len(stops) or len(trip_ids) != len(trips):
            raise ValueError("IDs principais repetidos")
        if any(t["route_id"] not in route_ids or t["shape_id"] not in shape_ids or t["service_id"] not in service_ids for t in trips):
            raise ValueError("Referências de route/shape/service inválidas")
        if any(t["stop_id"] not in stop_ids or t["trip_id"] not in trip_ids for t in times):
            raise ValueError("Referências stop_times inválidas")
        if any(not (-90 <= float(s["stop_lat"]) <= 90 and -180 <= float(s["stop_lon"]) <= 180) for s in stops):
            raise ValueError("Coordenadas de paradas inválidas")
        if not all([routes, trips, stops, times, shapes, calendars]):
            raise ValueError("Arquivos GTFS obrigatórios vazios")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "feed_type": "GTFS Static",
        "source": source.name,
        "source_sha256": digest,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "rows": {"routes": len(routes), "trips": len(trips), "stops": len(stops),
                 "stop_times": len(times), "shapes": len(shapes), "calendar": len(calendars)},
        "route_short_names": len({r["route_short_name"] for r in routes}),
        "network_ids": len({r.get("network_id", "") for r in routes if r.get("network_id")}),
        "shape_ids": len(shape_ids),
        "service_dates": {"start": min(c["start_date"] for c in calendars),
                          "end": max(c["end_date"] for c in calendars)},
        "notes": [
            "Horários do GTFS Static são programação e não GPS observado.",
            "Campos de horário ausentes permanecem ausentes; não interpolar.",
            "Identificadores GTFS não são automaticamente equivalentes aos IDs TACOM.",
            "fare_attributes com 0.0 não confirma gratuidade.",
        ],
    }



def publish_geography(source: Path, output: Path) -> dict:
    """GeoJSON derivados: identificadores GTFS sem misturar com a base TACOM."""
    from collections import defaultdict

    with zipfile.ZipFile(source) as archive:
        raw_stops = rows(archive, "stops.txt")
        raw_routes = rows(archive, "routes.txt")
        raw_trips = rows(archive, "trips.txt")
        raw_times = rows(archive, "stop_times.txt")
        raw_shapes = rows(archive, "shapes.txt")

    trip_to_route = {r["trip_id"]: r["route_id"] for r in raw_trips}
    routes_by_stop: dict[str, set[str]] = defaultdict(set)
    for entry in raw_times:
        routes_by_stop[entry["stop_id"]].add(trip_to_route[entry["trip_id"]])

    shapes_to_routes: dict[str, set[str]] = defaultdict(set)
    for trip in raw_trips:
        shapes_to_routes[trip["shape_id"]].add(trip["route_id"])

    route_codes = {route["route_id"]: route["route_short_name"] for route in raw_routes}
    stop_features = []
    for entry in raw_stops:
        route_ids = sorted(routes_by_stop[entry["stop_id"]])
        stop_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(entry["stop_lon"]), float(entry["stop_lat"])]},
            "properties": {
                "stop_id": entry["stop_id"], "name": entry["stop_name"],
                "gtfs_route_ids": route_ids,
                "gtfs_route_codes": sorted({route_codes[route_id] for route_id in route_ids}),
                "source": "GTFS Static", "status": "reference", "homologated": False,
            },
        })

    grouped_shapes: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for entry in raw_shapes:
        grouped_shapes[entry["shape_id"]].append(
            (int(entry["shape_pt_sequence"]), float(entry["shape_pt_lon"]), float(entry["shape_pt_lat"]))
        )
    shape_features = []
    for shape_id, coordinates in sorted(grouped_shapes.items()):
        route_ids = sorted(shapes_to_routes[shape_id])
        shape_features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for _, lon, lat in sorted(coordinates)],
            },
            "properties": {
                "shape_id": shape_id,
                "gtfs_route_ids": route_ids,
                "gtfs_route_codes": sorted({route_codes[route_id] for route_id in route_ids}),
                "source": "GTFS Static", "status": "reference", "homologated": False,
            },
        })

    def write(name: str, features: list[dict]) -> None:
        (output / name).write_text(
            json.dumps(
                {"type": "FeatureCollection", "features": features},
                ensure_ascii=False, separators=(",", ":"),
            ) + "\n",
            encoding="utf-8",
        )

    write("gtfs-paradas.geojson", stop_features)
    write("gtfs-itinerarios.geojson", shape_features)
    return {"stops": len(stop_features), "shapes": len(shape_features)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="ZIP GTFS de origem, não modificado")
    parser.add_argument("--output", type=Path, default=Path("public/data"))
    args = parser.parse_args()
    manifest = audit(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "gtfs-canoas.zip"
    if args.source.resolve() != destination.resolve():
        shutil.copyfile(args.source, destination)
    manifest['geodata'] = publish_geography(destination, args.output)
    (args.output / "gtfs-feed-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
