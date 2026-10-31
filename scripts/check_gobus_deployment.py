"""Aceite operacional da API HTTPS municipal, sem expor IDs e coordenadas.

Executa exatamente dois GET (health + vehicles), sem publicar corpo da resposta.
Não verifica servidores HTTP da TACOM nem estima viagens/ETA.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import ipaddress
import json
from urllib.parse import urlsplit
import httpx

from transporte.audit import timestamp
from transporte.geo import valid_coordinate


def approved_base(url: str, allow_local_http: bool = False) -> str:
    parsed = urlsplit(url.rstrip("/"))
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("API não deve conter credenciais, query ou fragmento")
    local = False
    try:
        local = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        local = (parsed.hostname or "").lower() == "localhost"
    if parsed.path not in ("", "/"):
        raise ValueError("Informar somente a origem da API, sem caminho")
    if parsed.scheme != "https" and not (
        allow_local_http and parsed.scheme == "http" and local
    ):
        raise ValueError("API pública precisa ser HTTPS")
    if not parsed.hostname:
        raise ValueError("Host da API obrigatório")
    return url.rstrip("/")


def check(base_url, *, client: httpx.Client, allow_local_http=False,
          clock=lambda:datetime.now(timezone.utc)) -> dict:
    base = approved_base(base_url, allow_local_http)
    health = client.get(base + "/v1/health", follow_redirects=False, timeout=12)
    health.raise_for_status()
    response = client.get(base + "/v1/vehicles", follow_redirects=False, timeout=12)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or body.get("status") not in (
        "reference", "available", "unavailable"
    ) or not isinstance(body.get("vehicles"), list):
        raise ValueError("Contrato da API pública inválido")
    status = body["status"]
    rows = body["vehicles"]
    if status == "unavailable" and rows:
        raise ValueError("API expôs posições sem autorização de publicação")
    quality = Counter()
    errors = Counter()
    now = clock()
    for row in rows:
        if not isinstance(row, dict):
            errors["invalid_record"] += 1
            continue
        if not valid_coordinate(row.get("longitude"), row.get("latitude")):
            errors["out_of_area"] += 1
        time_basis = row.get("time_basis")
        quality[str(time_basis)] += 1
        signal = row.get("signal_status")
        if signal not in ("SC", "SG", "ok"):
            errors["invalid_signal"] += 1
        if signal in ("SC", "SG") and row.get("bearing") is not None:
            errors["bearing_with_unavailable_signal"] += 1
        try:
            fetched = timestamp(row.get("fetched_at"))
            observed = timestamp(row.get("observed_at"))
            age = (now - fetched).total_seconds()
            if age > 180 or age < -30:
                errors["expired_or_future"] += 1
            if time_basis == "client_fetch":
                if (fetched - observed).total_seconds() > 1 or (
                    observed - fetched).total_seconds() > 1:
                    errors["client_fetch_timestamp_mismatch"] += 1
                if row.get("source_observed_at") is not None:
                    errors["source_timestamp_fabricated"] += 1
                if row.get("speed_kmh") is not None:
                    errors["unsupported_speed"] += 1
        except (TypeError, ValueError):
            errors["invalid_timestamp"] += 1
        if status == "available" and time_basis != "source_gps":
            errors["unhomologated_position_as_available"] += 1
    return {
        "api_reachable":True, "health_status":health.json().get("status"),
        "publication_status":status, "vehicles_in_snapshot":len(rows),
        "time_bases":dict(quality), "validation_errors":dict(errors),
        "valid":not errors,
        "limitation":"Nenhuma ausência de posição comprova ausência de viagem; sem coordenadas/IDs nos logs."
    }


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--api",required=True,help="Origem HTTPS da API municipal, sem credenciais")
    cli.add_argument("--allow-local-http",action="store_true")
    args=cli.parse_args()
    with httpx.Client(trust_env=False) as client:
        result=check(args.api,client=client,allow_local_http=args.allow_local_http)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    if not result["valid"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
