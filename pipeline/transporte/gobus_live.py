"""Leitura GPS TACOM/GoBus MPA, estritamente GET e sob autorização explícita.

Descoberta por previsões de paradas verificadas; sem enumeração de itinerários,
sem efeitos colaterais, sem dados brutos no Pages. Fetched_at NÃO é o timestamp
do equipamento embarcado. O feed permanece privado até homologação de publicação.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import time
from collections import defaultdict
from typing import Callable

import httpx

from .geo import MunicipalReferenceArea, valid_coordinate
from .gobus import payload, predictions, request_path, vehicles
from .persistence import atomic_json

BASE = "http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/"
SOURCE_ID = "TACOM-SIU-MPA"
MUNICIPALITY = "4304606"


def code(value):
    text = str(value or "").strip()
    if not text.isdecimal():
        return ""
    return text.lstrip("0") or "0"


def iso(dt: datetime):
    if dt.tzinfo is None:
        raise ValueError("Relógio exige fuso horário")
    return dt.astimezone(timezone.utc).isoformat()


def reference_shapes(document):
    """Mapa de itinerários observados na TACOM, nunca por semelhança de nomes."""
    index = {}
    ambiguous = set()
    if document.get("type") != "FeatureCollection":
        raise ValueError("GeoJSON de referência inválido")
    for f in document.get("features", []):
        p = f.get("properties") or {}
        sid = str(p.get("itinerary_id") or "")
        route = str(p.get("route_id") or "")
        source_code = code(p.get("source_route_code"))
        if not (sid.isdecimal() and route and source_code and
                p.get("municipality_code") == MUNICIPALITY and
                p.get("association_method") == "city4_exact_code_and_prediction_itinerary"):
            continue
        if sid in index and index[sid] != (route, source_code):
            ambiguous.add(sid)
        index[sid] = (route, source_code)
    for sid in ambiguous:
        del index[sid]
    return index


def selected_stops(inventory, valid_routes, offset=0, count=8):
    if inventory.get("municipality_code") != MUNICIPALITY or inventory.get("city_id") != "4":
        raise ValueError("Inventário de parada fora do município TACOM validado")
    stops = sorted({
        str(r["stop_id"]) for r in inventory.get("stops", [])
        if r.get("status") == "located" and str(r.get("stop_id", "")).isdecimal()
        and any(str(x) in valid_routes for x in r.get("route_ids", []))
    }, key=int)
    if not stops or count <= 0:
        return []
    # Estratificação sobre o inventário inteiro, não somente sobre o centro.
    n = min(count, len(stops))
    return [stops[(offset + (i * len(stops)) // n) % len(stops)] for i in range(n)]


class LiveCollector:
    def __init__(
        self, client: httpx.Client, *, spacing=15.0, max_requests=16,
        retries=2, clock: Callable=lambda: datetime.now(timezone.utc),
        monotonic: Callable=time.monotonic, sleep: Callable=time.sleep,
        jitter: Callable=lambda: random.uniform(0, 1),
        state=None, cache=None, max_per_hour=120, max_per_day=1000
    ):
        if (spacing < 15 or max_requests < 1 or max_requests > 60 or
                not 0 <= retries <= 2 or
                not 1 <= max_per_hour <= 3600 or
                not max_per_hour <= max_per_day <= 50000):
            raise ValueError("Limites de frequência/orçamento inválidos")
        self.client = client
        self.spacing = float(spacing)
        self.maximum = int(max_requests)
        self.max_per_hour = int(max_per_hour)
        self.max_per_day = int(max_per_day)
        self.retries = retries
        self.clock = clock
        self.monotonic = monotonic
        self.sleep = sleep
        self.jitter = jitter
        self.state = dict(state or {})
        self.state.setdefault("cursor", 0)
        self.state.setdefault("positions", {})
        self.state.setdefault("requests_utc", [])
        self.state.setdefault("cycle", 0)
        self.cache = cache if cache is not None else {}
        self.requests = 0
        self.cache_hits = 0
        self.last = None
        self.denied = False
        self.exhausted = False
        self.throttled = False

    def get(self, kind, **params):
        if kind not in ("previsoes", "veiculos"):
            raise ValueError("Sonda ao vivo só permite previsões e veículos")
        path = request_path(kind, **params)
        key = (kind, path)
        now = self.clock()
        ttl = 30 if kind == "previsoes" else 15
        cached = self.cache.get(key)
        if cached and 0 <= (now - cached[1]).total_seconds() < ttl:
            self.cache_hits += 1
            return cached[0], iso(cached[1])
        if self.denied:
            raise ValueError("Acesso suspenso por erro de autorização")
        for attempt in range(self.retries + 1):
            if self.requests >= self.maximum:
                self.exhausted = True
                raise ValueError("Orçamento do ciclo TACOM esgotado")
            # Orçamento acumulado persistido entre rodadas/reinicializações.
            # Tentativas de retry também são contabilizadas.
            seen = []
            for item in self.state["requests_utc"]:
                try:
                    at = datetime.fromisoformat(item)
                    if at.tzinfo and 0 <= (self.clock() - at).total_seconds() < 86400:
                        seen.append(item)
                except (TypeError,ValueError):
                    continue
            self.state["requests_utc"] = seen
            hour = sum((self.clock() - datetime.fromisoformat(x)).total_seconds() < 3600 for x in seen)
            if hour >= self.max_per_hour or len(seen) >= self.max_per_day:
                self.exhausted = True
                raise ValueError("Orçamento TACOM acumulado esgotado")
            if self.last is not None:
                self.sleep(max(0, self.spacing - (self.monotonic() - self.last)) + self.jitter())
            self.last = self.monotonic()
            self.requests += 1
            self.state['requests_utc'].append(iso(self.clock()))
            try:
                callback = path.rsplit("/", 1)[-1]
                response = self.client.get(
                    BASE + path, params={"callback": callback, "_": int(self.clock().timestamp() * 1000)},
                    headers={"User-Agent": "GeoCanoasTransporte-AuthorizedReadOnly/0.5",
                             "Accept": "application/javascript,application/json,text/plain"},
                    follow_redirects=False,
                    timeout=45,
                )
                if response.status_code == 429:
                    self.throttled = True
                if response.status_code in (401, 403):
                    self.denied = True
                    raise ValueError("Acesso TACOM negado; consultas suspensas")
                if 300 <= response.status_code < 400:
                    raise ValueError("Redirecionamento proibido")
                if response.status_code in (408, 429, 500, 502, 503, 504):
                    if attempt < self.retries:
                        delay = min(30, 2 ** (attempt + 2))
                        if response.status_code == 429:
                            try:
                                requested = float(response.headers.get("Retry-After", "0"))
                            except ValueError:
                                requested = 31
                            if requested > 30:
                                raise ValueError("Limite TACOM excedido; suspensão")
                            delay = max(delay, requested)
                        self.sleep(delay + self.jitter())
                        continue
                response.raise_for_status()
                if len(response.content) > 2_000_000:
                    raise ValueError("Resposta TACOM acima de 2 MB")
                doc = payload(response.content.decode("utf-8-sig"))
                fetched = self.clock()
                self.cache[key] = (doc, fetched)
                return doc, iso(fetched)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt < self.retries:
                    self.sleep(min(30, 2 ** (attempt + 2)) + self.jitter())
                    continue
                raise
        raise ValueError("Consulta não concluída")

    def once(self, inventory, shapes, neighborhoods, *, stop_queries=8, itinerary_queries=6):
        if not 1 <= stop_queries <= 30 or not 1 <= itinerary_queries <= 30:
            raise ValueError("Limite de paradas/itinerários inválido")
        index = reference_shapes(shapes)
        valid_routes = {v[0] for v in index.values()}
        area = MunicipalReferenceArea(neighborhoods)
        ids = selected_stops(inventory, valid_routes, self.state["cursor"], stop_queries)
        self.state["cursor"] += 1
        self.state["cycle"] += 1
        cycle = self.state["cycle"]
        active = defaultdict(set)
        failures = []
        # O par (itinerário, veículo) é observado em previsão, nunca adivinhado.
        for stop_id in ids:
            if self.requests >= self.maximum or self.denied or self.exhausted or self.throttled:
                break
            try:
                raw, _ = self.get("previsoes", parada=stop_id, acessivel="false", cidade="MPA")
                for p in predictions(json.dumps(raw)):
                    itinerary_id = str(p.get("codItinerario") or "")
                    vehicle_id = str(p.get("numVeicGestor") or "").strip()
                    pair = index.get(itinerary_id)
                    if not pair or not vehicle_id or not vehicle_id.isdecimal():
                        continue
                    if code(p.get("sgLin")) != pair[1]:
                        continue
                    active[itinerary_id].add(vehicle_id)
            except (ValueError, httpx.HTTPError):
                failures.append("previsoes")
                if self.denied:
                    break
        positions = []
        fetched_ids = set()
        for itinerary_id in sorted(active, key=int)[:itinerary_queries]:
            if self.requests >= self.maximum or self.denied or self.exhausted or self.throttled:
                break
            try:
                raw, fetched_at = self.get("veiculos", itinerario=itinerary_id, cidade="MPA")
                route_id, _ = index[itinerary_id]
                for row in vehicles(json.dumps(raw)):
                    vehicle_id = row["vehicle_id"]
                    if vehicle_id not in active[itinerary_id]:
                        continue
                    lon, lat = row["longitude"], row["latitude"]
                    if lon is None or lat is None or not valid_coordinate(lon, lat):
                        continue
                    if not area.point(lon, lat):
                        continue
                    key = SOURCE_ID + ":" + vehicle_id
                    if key in fetched_ids:
                        # Um mesmo ônibus em dois itinerários => vínculo ambíguo.
                        positions = [p for p in positions if p["vehicle_id"] != vehicle_id]
                        continue
                    fetched_ids.add(key)
                    previous = self.state["positions"].get(key, {})
                    unchanged = (
                        previous.get("last_seen_cycle") == cycle - 1 and
                        previous.get("itinerary_id") == itinerary_id and
                        previous.get("longitude") == lon and
                        previous.get("latitude") == lat
                    )
                    stale = min(9999, int(previous.get("stale_polls") or 0) + 1) if unchanged else 0
                    positions.append({
                        "source_id": SOURCE_ID, "vehicle_id": vehicle_id,
                        "route_id": route_id, "source_itinerary_id": itinerary_id,
                        "route_relation": "reference_not_homologated",
                        "scope": "municipal", "municipality_code": MUNICIPALITY,
                        "longitude": lon, "latitude": lat,
                        "observed_at": fetched_at, "fetched_at": fetched_at,
                        "source_observed_at": None, "time_basis": "client_fetch",
                        "signal_status": row["signal_status"],
                        "bearing": row["bearing"], "bearing_basis": row["bearing_basis"],
                        "speed_kmh": None, "stale_polls": stale
                    })
                    self.state["positions"][key] = {
                        "longitude": lon, "latitude": lat, "stale_polls": stale,
                        "fetched_at": fetched_at, "last_seen_cycle": cycle,
                        "itinerary_id": itinerary_id
                    }
            except (ValueError, httpx.HTTPError):
                failures.append("veiculos")
                if self.denied:
                    break
        # Não perpetuar indefinidamente IDs de veículos a partir de snapshots antigos.
        self.state["positions"] = {
            k: v for k, v in self.state["positions"].items()
            if (self.clock() - datetime.fromisoformat(v["fetched_at"])).total_seconds() < 3600
        }
        return {
            "status": "reference" if positions else "no_positions_observed",
            "generated_at": iso(self.clock()),
            "source_id": SOURCE_ID, "municipality_code": MUNICIPALITY,
            "time_basis": "client_fetch",
            "vehicles": positions,
            "diagnostics": {
                "sampled_stops": len(ids),
                "active_itineraries": len(active),
                "queried_itineraries": min(len(active), itinerary_queries),
                "requests": self.requests, "cache_hits": self.cache_hits,
                "failures": len(failures), "access_denied": self.denied,
                "rate_limited": self.throttled, "quota_exhausted": self.exhausted,
                "requests_last_hour": sum(
                    0 <= (self.clock() - datetime.fromisoformat(x)).total_seconds() < 3600
                    for x in self.state["requests_utc"]
                ),
                "requests_last_day": len(self.state["requests_utc"])
            }
        }


def private_path(root, supplied):
    root = Path(root).resolve()
    folder = (root / "var" / "gobus").resolve()
    path = Path(supplied).resolve()
    if not path.is_relative_to(folder):
        raise ValueError("Saída e estado devem permanecer em var/gobus, nunca em public/ ou dist/")
    return path


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--authorized", action="store_true")
    cli.add_argument("--accept-plain-http", action="store_true")
    cli.add_argument("--continuous", action="store_true", help="Somente processo persistente privado, não CI")
    cli.add_argument("--interval", type=float, default=15, help="Mínimo entre GET (>=15 s)")
    cli.add_argument("--cycle-interval", type=int, default=180)
    cli.add_argument("--max-requests", type=int, default=16)
    cli.add_argument("--max-per-hour", type=int, default=120)
    cli.add_argument("--max-per-day", type=int, default=1000)
    cli.add_argument("--stop-queries", type=int, default=8)
    cli.add_argument("--itinerary-queries", type=int, default=6)
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    cli.add_argument("--output", type=Path)
    cli.add_argument("--state", type=Path)
    args = cli.parse_args()
    if not args.authorized or not args.accept_plain_http:
        cli.error("Exige autorização e ciência de que a origem é HTTP sem TLS")
    if args.cycle_interval < 60:
        cli.error("O ciclo não pode ser inferior a 60 segundos")
    root = args.root.resolve()
    output = private_path(root, args.output or root / "var/gobus/live-feed.json")
    state_path = private_path(root, args.state or root / "var/gobus/live-state.json")
    data = root / "public/data"
    inventory = json.loads((data / "stop-inventory.json").read_text())
    shapes = json.loads((data / "route-shapes.geojson").read_text())
    neighborhoods = json.loads((data / "bairros-oficiais.geojson").read_text())
    previous = json.loads(state_path.read_text()) if state_path.is_file() else {}
    cache = {}  # Cache exclusivamente em memória, nunca no GitHub Pages.
    with httpx.Client(follow_redirects=False, trust_env=False) as client:
        while True:
            collector = LiveCollector(client, cache=cache, spacing=args.interval,
                                      max_requests=args.max_requests, state=previous,
                                      max_per_hour=args.max_per_hour,
                                      max_per_day=args.max_per_day)
            report = collector.once(inventory, shapes, neighborhoods,
                                    stop_queries=args.stop_queries,
                                    itinerary_queries=args.itinerary_queries)
            output.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(output, report)
            atomic_json(state_path, collector.state)
            # Nenhuma posição, placa, ID ou resposta bruta vai para os logs.
            print(json.dumps({"status": report["status"],
                              "vehicles_observed": len(report["vehicles"]),
                              **report["diagnostics"]}), flush=True)
            if not args.continuous or collector.denied:
                break
            previous = collector.state
            time.sleep(args.cycle_interval)


if __name__ == "__main__":
    main()
