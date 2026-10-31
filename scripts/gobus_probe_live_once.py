"""Sonda PONTUAL e sanitizada do GoBus: somente contagens, sem GPS público.

GET em 6 paradas verificadas no inventário e até 3 itinerários descobertos.
Exige autorização e aviso do HTTP sem TLS. Não grava resposta bruta ou IDs.
"""
from collections import Counter
from pathlib import Path
import argparse
import json
import httpx
from transporte.gobus_live import LiveCollector

def run(root):
    root=Path(root)
    data=root/"public/data"
    inventory=json.loads((data/"stop-inventory.json").read_text())
    shapes=json.loads((data/"route-shapes.geojson").read_text())
    neighborhoods=json.loads((data/"bairros-oficiais.geojson").read_text())
    # Validação do próprio catálogo publicado, sem utilizar coordenadas arbitrárias.
    if inventory.get("municipality_code")!="4304606" or inventory.get("city_id")!="4":
        raise ValueError("Inventário de Canoas inválido")
    with httpx.Client(follow_redirects=False,trust_env=True) as client:
        collector=LiveCollector(client,spacing=15,max_requests=10,retries=0)
        result=collector.once(inventory,shapes,neighborhoods,stop_queries=6,itinerary_queries=3)
    return {
        "status": result["status"],
        "vehicles_observed": len(result["vehicles"]),
        "signal_counts": dict(Counter(v["signal_status"] for v in result["vehicles"])),
        "sampled_stops": result["diagnostics"]["sampled_stops"],
        "active_itineraries": result["diagnostics"]["active_itineraries"],
        "source_queries": result["diagnostics"]["requests"],
        "access_denied": result["diagnostics"]["access_denied"],
        "limitation": "Amostra momentânea; sem timestamp GPS original, sem publicação dos dados."
    }

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--authorized",action="store_true")
    cli.add_argument("--accept-plain-http",action="store_true")
    cli.add_argument("--root",default=Path(__file__).resolve().parents[1],type=Path)
    args=cli.parse_args()
    if not (args.authorized and args.accept_plain_http):
        cli.error("Exige autorização e reconhecimento do HTTP sem TLS")
    report=run(args.root)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
