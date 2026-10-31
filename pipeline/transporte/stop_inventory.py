"""Plano de consultas espaciais e completude do recorte de paradas observado.

Centros da grade são locais de consulta à API, nunca paradas estimadas.
"""

import copy
import math
from collections import Counter
from shapely.geometry import Point, box
from shapely.ops import nearest_points, transform
from .geo import UNPROJECT


def grid_queries(area, spacing=700):
    if not 400 <= spacing <= 1000:
        raise ValueError("Espaçamento da grade deve ficar entre 400 e 1000 metros")
    west, south, east, north = area.area.bounds
    points = []
    for x in range(math.floor(west / spacing), math.floor(east / spacing) + 1):
        for y in range(math.floor(south / spacing), math.floor(north / spacing) + 1):
            cell = box(x * spacing, y * spacing, (x + 1) * spacing, (y + 1) * spacing)
            intersection = area.area.intersection(cell)
            if intersection.is_empty or intersection.area == 0:
                continue
            center = cell.centroid
            seed = (
                center
                if intersection.covers(center)
                else nearest_points(intersection, center)[0]
            )
            points.append(transform(UNPROJECT, seed))
    return points


def refresh_inventory(inventory, published_features):
    """Contagens usam IDs únicos conhecidos, não soma de vínculos nem total municipal."""
    inventory = copy.deepcopy(inventory)
    located = {str(f["properties"]["stop_id"]) for f in published_features}
    for row in inventory["stops"]:
        if row["stop_id"] in located:
            row["status"] = "located"
        elif row["status"] == "located":
            row["status"] = "pending"
    status = dict(Counter(row["status"] for row in inventory["stops"]))
    known = len(inventory["stops"])
    found = status.get("located", 0)
    inventory.update(
        source_stop_ids=known,
        located_stop_ids=found,
        unlocated_stop_ids=known - found,
        localization_pct=round(100 * found / known, 2) if known else None,
        status_counts=status,
    )
    for route in inventory["routes"]:
        rows = [s for s in inventory["stops"] if route["route_id"] in s["route_ids"]]
        total = len(rows)
        count = sum(s["status"] == "located" for s in rows)
        route.update(
            known_stop_ids=total,
            located_stop_ids=count,
            unlocated_stop_ids=total - count,
            localization_pct=round(100 * count / total, 2) if total else None,
        )
    return inventory


def build_inventory(
    links, labels, sources, features, statuses, generated_at, catalogue_count
):
    inventory = {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "matched_municipal_line_lists_reference",
        "municipality_code": "4304606",
        "city_id": "4",
        "catalogue_routes": catalogue_count,
        "source_lines_successful": len(sources),
        "routes": [
            {
                "route_id": rid,
                "source_url": source["url"],
                "source_sha256": source["sha256"],
                "fetched_at": source["fetched_at"],
            }
            for rid, source in sorted(sources.items())
        ],
        "stops": [
            {
                "stop_id": sid,
                "name": labels.get(sid) or "Sem nome publicado",
                "route_ids": sorted(routes),
                "status": statuses.get(sid, "pending"),
            }
            for sid, routes in sorted(links.items())
        ],
        "limitations": [
            "Completude somente dos IDs das listas consultadas; não é inventário completo ou homologado do município.",
            "IDs podem representar sentidos, plataformas e versões diferentes; não são deduplicados por proximidade.",
            "IDs sem coordenadas não são plotados nem atribuídos a bairro por aproximação.",
            "Ponto ausente no mapa não comprova ausência de serviço; ponto publicado não comprova operação atual.",
        ],
    }
    return refresh_inventory(inventory, features)
