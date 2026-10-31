"""Coleta geográfica de referência TACOM, sem GPS e sem inferir percursos.

A relação linha-itinerário é observada nas previsões de paradas da própria linha.
Coordenadas por linha não são utilizadas: o endpoint retornou dados de Viamão.
"""

from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo
from shapely import make_valid
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union
from .collect import dump
from .geo import PROJECT, MunicipalReferenceArea as LocalArea
from .gobus import (
    line_cities,
    lines,
    stops,
    predictions,
    itinerary,
    request_path,
    payload,
)
from .gobus_crosswalk import normalized
from .http import utcnow

BASE = "http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/"
METHOD = "gobus-geography-0.3.0"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Redirecionamento não permitido")


class Reader:
    def __init__(self, folder, interval=2, max_requests=180):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.interval = max(1.5, interval)
        self.maximum = min(300, max_requests)
        self.count = 0
        self.last = 0.0
        self.lock = threading.Lock()
        self.denied = False
        self.records = []

    def archive(self, item):
        history = self.folder.parent / "source-history"
        history.mkdir(parents=True, exist_ok=True)
        identity = hashlib.sha256(
            (item["url"] + item["fetched_at"] + item["sha256"]).encode()
        ).hexdigest()
        target = history / (identity + ".json")
        if not target.exists():
            dump(target, item)

    def get(self, kind, **params):
        url = BASE + request_path(kind, **params)
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.folder / (key + ".json")
        ttl = 300 if kind == "previsoes" else 86400
        if path.exists():
            cached = json.loads(path.read_text())
            self.archive(cached)
            if (
                time.time() - datetime.fromisoformat(cached["fetched_at"]).timestamp()
                < ttl
            ):
                return payload(cached["body"]), {
                    k: v for k, v in cached.items() if k != "body"
                }
        with self.lock:
            if self.denied:
                raise ValueError("Fonte negou acesso; coleta interrompida")
            if self.count >= self.maximum:
                raise ValueError("Orçamento de requisições atingido")
            time.sleep(max(0, self.interval - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            self.count += 1
        opener = urllib.request.build_opener(NoRedirect)
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "GeoCanoasTransporte-AuthorizedResearch/0.3",
                    "Accept": "application/javascript,application/json,text/plain",
                },
            )
            with opener.open(request, timeout=25) as response:
                raw = response.read(5_000_001)
                if len(raw) > 5_000_000:
                    raise ValueError("Resposta acima de 5 MB")
                if response.status != 200:
                    raise ValueError("HTTP diferente de 200")
            body = raw.decode("utf-8-sig")
            document = payload(body)
            item = {
                "url": url,
                "fetched_at": utcnow(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "kind": kind,
                "params": params,
                "body": body,
            }
            self.archive(item)
            dump(path, item)
            with self.lock:
                self.records.append({k: v for k, v in item.items() if k != "body"})
            return document, {k: v for k, v in item.items() if k != "body"}
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                self.denied = True
            raise


def collect(
    root,
    *,
    reader,
    service_date=None,
    geo_samples=18,
    prediction_samples=10,
    max_itineraries=64,
):
    root = Path(root)
    data = root / "public/data"
    network = json.loads((data / "network.json").read_text())
    neighborhoods = json.loads((data / "bairros-oficiais.geojson").read_text())
    area = LocalArea(neighborhoods)
    errors = []

    def read(kind, **params):
        try:
            return reader.get(kind, **params)
        except Exception as error:
            errors.append(
                {
                    "resource": kind,
                    "params": params,
                    "error": type(error).__name__ + ": " + str(error)[:180],
                }
            )
            return None

    city = read("cidades_linhas", cidade="MPA")
    catalogue = read("linhas")
    if not city or not catalogue:
        raise ValueError("Não foi possível validar catálogo/cidade")
    if [
        x["city_id"]
        for x in line_cities(json.dumps(city[0]))
        if x["name"].strip().upper() == "CANOAS"
    ] != ["4"]:
        raise ValueError("Canoas/codcid=4 não confirmado")
    municipal = [
        r
        for r in lines(json.dumps(catalogue[0]))
        if r.get("praca") == "MPA" and str(r.get("codcid")) == "4"
    ]
    source_by_code = defaultdict(list)
    for row in municipal:
        source_by_code[normalized(row["sgl"])].append(row)
    official = {normalized(r["code"]): r for r in network["routes"]}
    matches = {
        code: (values[0], official[code])
        for code, values in source_by_code.items()
        if len(values) == 1 and code in official
    }
    target = {
        code: value
        for code, value in matches.items()
        if not service_date or service_date in value[1]["dates"]
    }
    links = defaultdict(set)
    directions = defaultdict(lambda: defaultdict(set))
    relation_evidence = {}
    source_stop_labels = {}
    origin_ids = []

    def line_task(item):
        code, (source, route) = item
        return code, read("paradas_linha", linha=str(source["cod"]), cidade="MPA")

    with ThreadPoolExecutor(max_workers=2) as pool:
        for code, result in pool.map(line_task, target.items()):
            if result:
                doc, evidence = result
                rid = target[code][1]["id"]
                relation_evidence[rid] = evidence
                parsed_stops = stops(json.dumps(doc))
                if parsed_stops and parsed_stops[0]["stop_id"].isdecimal():
                    origin_ids.append(parsed_stops[0]["stop_id"])
                for stop in parsed_stops:
                    sid = stop["stop_id"]
                    if not sid.isdecimal():
                        continue
                    links[sid].add(rid)
                    source_stop_labels[sid] = stop.get("label")
                    if stop.get("sentido"):
                        directions[sid][rid].add(str(stop["sentido"]))
    print(
        json.dumps(
            {
                "phase": "line_stop_ids",
                "routes": len(relation_evidence),
                "unique_ids": len(links),
                "requests": reader.count,
            }
        ),
        flush=True,
    )
    coordinate_records = {}
    conflicts = set()

    def add_points(result):
        if not result:
            return
        doc, evidence = result
        for stop in stops(json.dumps(doc)):
            if "longitude" not in stop or not area.point(
                stop["longitude"], stop["latitude"]
            ):
                continue
            sid = stop["stop_id"]
            if sid in coordinate_records:
                old = coordinate_records[sid][0]
                if (
                    transform(
                        PROJECT, Point(old["longitude"], old["latitude"])
                    ).distance(
                        transform(PROJECT, Point(stop["longitude"], stop["latitude"]))
                    )
                    > 10
                ):
                    conflicts.add(sid)
            else:
                coordinate_records[sid] = (stop, evidence)

    # Pontos de consulta reais, distribuídos em células censitárias habitadas de 1 km.
    sectors = json.loads((data / "censo2022-setores.geojson").read_text())
    cells = {}
    for f in sectors["features"]:
        population = float(f["properties"].get("pop") or 0)
        if population <= 0:
            continue
        p = shape(f["geometry"]).representative_point()
        metric = transform(PROJECT, p)
        cell = (int(metric.x // 1000), int(metric.y // 1000))
        if cell not in cells or population > cells[cell][0]:
            cells[cell] = (population, p)
    ranked = sorted(cells.values(), key=lambda item: -item[0])
    seeds = []
    represented = set()
    for _, point in ranked:
        name = area.neighborhood(point.x, point.y)
        if name and name not in represented:
            seeds.append(point)
            represented.add(name)
        if len(seeds) >= geo_samples:
            break
    for _, point in ranked:
        if len(seeds) >= geo_samples:
            break
        if not any(p.equals(point) for p in seeds):
            seeds.append(point)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(
            lambda p: read(
                "paradas_proximas",
                longitude=round(p.x, 6),
                latitude=round(p.y, 6),
                cidade="MPA",
            ),
            seeds,
        ):
            add_points(result)
    unresolved = list(
        dict.fromkeys(sid for sid in origin_ids if sid not in coordinate_records)
    )[:12]
    unresolved.extend(
        sid
        for sid in sorted(links, key=lambda sid: (-len(links[sid]), sid))
        if sid not in coordinate_records
        and sid not in unresolved
        and len(unresolved) < 12
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(
            lambda sid: read("parada_detalhes", parada=sid), unresolved
        ):
            add_points(result)
    print(
        json.dumps(
            {
                "phase": "stop_coordinates",
                "coordinates": len(coordinate_records),
                "linked": sum(sid in links for sid in coordinate_records),
                "requests": reader.count,
            }
        ),
        flush=True,
    )
    eligible = sorted(
        (sid for sid in coordinate_records if sid in links and sid not in conflicts),
        key=lambda sid: (-len(links[sid]), sid),
    )
    # Distribuir a amostra pelo território, evitando que todas as consultas sejam no mesmo terminal.
    sampled = []
    used_cells = set()
    for sid in eligible:
        s = coordinate_records[sid][0]
        p = transform(PROJECT, Point(s["longitude"], s["latitude"]))
        cell = (int(p.x // 1200), int(p.y // 1200))
        if cell not in used_cells:
            sampled.append(sid)
            used_cells.add(cell)
        if len(sampled) >= prediction_samples:
            break
    sampled.extend(
        sid
        for sid in eligible
        if sid not in sampled and len(sampled) < prediction_samples
    )
    relationships = defaultdict(list)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = pool.map(
            lambda sid: (
                sid,
                read("previsoes", parada=sid, acessivel="false", cidade="MPA"),
            ),
            sampled,
        )
        for sid, result in results:
            if not result:
                continue
            doc, evidence = result
            for prediction in predictions(json.dumps(doc)):
                code = normalized(prediction.get("sgLin"))
                iid = str(prediction.get("codItinerario") or "")
                if code in matches and iid.isdecimal() and iid != "0":
                    relationships[(code, iid)].append({"stop_id": sid, **evidence})
    # Incluir a amostra independente inicialmente validada, se ainda estiver na janela do cache.
    if "8746" in links and "8746" not in sampled:
        result = read("previsoes", parada="8746", acessivel="false", cidade="MPA")
        if result:
            for prediction in predictions(json.dumps(result[0])):
                code = normalized(prediction.get("sgLin"))
                iid = str(prediction.get("codItinerario") or "")
                if code in matches and iid.isdecimal() and iid != "0":
                    relationships[(code, iid)].append({"stop_id": "8746", **result[1]})
    candidates = sorted(
        relationships,
        key=lambda x: (sum(1 for c, i in relationships if c == x[0]), x[0], x[1]),
    )
    # Primeiro um itinerário por linha; depois variantes adicionais.
    ordered = []
    seen_codes = set()
    for pair in candidates:
        if pair[0] not in seen_codes:
            ordered.append(pair)
            seen_codes.add(pair[0])
    ordered.extend(pair for pair in candidates if pair not in ordered)
    ordered = ordered[:max_itineraries]
    routes = []
    bad_shapes = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = pool.map(
            lambda pair: (pair, read("itinerario", itinerario=pair[1], cidade="MPA")),
            ordered,
        )
        for (code, iid), result in results:
            if not result:
                continue
            doc, evidence = result
            try:
                feature = itinerary(json.dumps(doc), iid)
                quality = area.line(feature)
                if (
                    quality["local_length_pct"] < 80
                    or quality["max_boundary_distance_m"] > 1500
                    or not 0.2 <= quality["length_km"] <= 100
                ):
                    raise ValueError("Geometria incompatível com a área de Canoas")
                source, route = matches[code]
                feature["properties"].update(
                    {
                        "route_id": route["id"],
                        "shape_id": "SIU-" + iid,
                        "direction": "Sentido não informado pela API",
                        "siu_line_id": str(source["cod"]),
                        "source_route_code": source["sgl"],
                        "source_route_name": source["nom"],
                        "source": "TACOM-GoBus",
                        "source_name": "TACOM / SIU Mobile MPA",
                        "source_url": evidence["url"],
                        "source_sha256": evidence["sha256"],
                        "fetched_at": evidence["fetched_at"],
                        "reference_date": evidence["fetched_at"][:10],
                        "municipality_code": "4304606",
                        "status": "reference",
                        "homologated": False,
                        "association_method": "city4_exact_code_and_prediction_itinerary",
                        "schedule_equivalence": "not_homologated",
                        "territorial_quality": (
                            "border_review"
                            if quality["local_length_pct"] < 95
                            else "compatible"
                        ),
                        "prediction_evidence_sha256": relationships[(code, iid)][0][
                            "sha256"
                        ],
                        "prediction_source_url": relationships[(code, iid)][0]["url"],
                        "validity": "not_published_by_source",
                        "method": METHOD,
                        **quality,
                    }
                )
                routes.append(feature)
            except Exception as error:
                bad_shapes.append(
                    {"itinerary_id": iid, "route_code": code, "reason": str(error)}
                )
    features = []
    for sid, (stop, evidence) in sorted(coordinate_records.items()):
        if sid not in links or sid in conflicts:
            continue
        lon, lat = stop["longitude"], stop["latitude"]
        features.append(
            {
                "type": "Feature",
                "id": "TACOM-" + sid,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "stop_id": sid,
                    "name": stop.get("label")
                    or source_stop_labels.get(sid)
                    or "Sem nome publicado",
                    "siu": stop.get("siu") or "",
                    "route_ids": sorted(links[sid]),
                    "route_ids_csv": ",".join(sorted(links[sid])),
                    "directions_by_route": {
                        k: sorted(v) for k, v in directions[sid].items()
                    },
                    "neighborhood": area.neighborhood(lon, lat),
                    "source": "TACOM-GoBus",
                    "source_name": "TACOM / SIU Mobile MPA",
                    "source_url": evidence["url"],
                    "source_sha256": evidence["sha256"],
                    "fetched_at": evidence["fetched_at"],
                    "municipality_code": "4304606",
                    "status": "reference",
                    "homologated": False,
                    "association_method": "source_line_stop_id_join",
                    "method": METHOD,
                },
            }
        )
    summary = {
        "schema_version": 1,
        "generated_at": utcnow(),
        "status": "partial_reference",
        "source_name": "TACOM / SIU Mobile MPA",
        "source_protocol": "HTTP sem TLS; integridade de origem não autenticada",
        "source_base_url": BASE,
        "municipality_code": "4304606",
        "city_id": "4",
        "source_lines": len(municipal),
        "code_matches": len(matches),
        "target_service_date": service_date,
        "queried_routes": len(target),
        "successful_stop_lists": len(relation_evidence),
        "source_stop_ids": len(links),
        "published_stops": len(features),
        "published_itineraries": len(routes),
        "routes_with_geometry": len({f["properties"]["route_id"] for f in routes}),
        "forecast_samples": len(sampled),
        "observed_itinerary_relations": len(relationships),
        "http_requests": reader.count,
        "conflicting_stops": sorted(conflicts),
        "border_review_itineraries": sum(
            f["properties"]["territorial_quality"] == "border_review" for f in routes
        ),
        "rejected_shapes": bad_shapes,
        "errors": errors,
        "missing_geometry_route_ids": sorted(
            r["id"]
            for r in network["routes"]
            if r["id"] not in {f["properties"]["route_id"] for f in routes}
        ),
        "line_stop_sources": relation_evidence,
        "limitations": [
            "Geometrias reais retornadas pela API; nenhuma linha foi reconstruída ligando paradas.",
            "Amostra parcial de itinerários encontrados em previsões; não cobre todas as variantes, sentidos ou datas.",
            "Correspondência NGS por código exato não homologa equivalência de programação ou vigência.",
            "Os pontos publicados têm ID associado a linha municipal do catálogo e coordenadas compatíveis com os bairros.",
            "O serviço de coordenadas por linha retornou Viamão e foi excluído da coleta.",
            "Percursos de borda: pelo menos 80% no buffer de 250 m e distância máxima de 1,5 km da união dos bairros; feições sinalizadas para revisão, sem recorte ou homologação de limite.",
            "Mapa de referência; não comprova operação atual, pontualidade ou cumprimento contratual.",
            "Consulta estática autorizada; não houve coleta contínua GPS nem publicação de identificadores de veículos.",
        ],
        "method": METHOD,
    }
    output = root / "var/gobus/geography"
    output.mkdir(parents=True, exist_ok=True)
    for filename, document in [
        (
            "route-shapes.geojson",
            {
                "type": "FeatureCollection",
                "features": routes,
                "status": "reference",
                "generated_at": summary["generated_at"],
            },
        ),
        (
            "stops.geojson",
            {
                "type": "FeatureCollection",
                "features": features,
                "status": "reference",
                "generated_at": summary["generated_at"],
            },
        ),
        ("transport-geography.json", summary),
    ]:
        dump(output / filename, document)
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k
                not in (
                    "line_stop_sources",
                    "errors",
                    "missing_geometry_route_ids",
                    "limitations",
                )
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--authorized", action="store_true")
    cli.add_argument("--allow-plain-http", action="store_true")
    cli.add_argument("--service-date")
    cli.add_argument("--max-requests", type=int, default=180)
    cli.add_argument("--geo-samples", type=int, default=18)
    cli.add_argument("--prediction-samples", type=int, default=10)
    cli.add_argument("--interval", type=float, default=2)
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = cli.parse_args()
    if not args.authorized or not args.allow_plain_http:
        cli.error("Exige autorização e uso explícito da origem HTTP legada")
    if args.service_date == "today":
        args.service_date = (
            datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
        )
    reader = Reader(
        args.root / "var/gobus/reference-cache", args.interval, args.max_requests
    )
    collect(
        args.root,
        reader=reader,
        service_date=args.service_date,
        geo_samples=min(args.geo_samples, 40),
        prediction_samples=min(args.prediction_samples, 20),
    )


if __name__ == "__main__":
    main()
