"""Worker privado GoBus: leitura autorizada -> normalização -> banco operacional.

Não transmite GPS em GitHub Actions/Pages. Não ativa publicação sem a variável
PUBLIC_POSITIONS_ENABLED definida explicitamente na API HTTPS de produção.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import signal
import time
import uuid
import httpx

from .audit import normalize_position
from .gobus_live import LiveCollector
from .http import utcnow
from .persistence import atomic_json
from .store import Store

STOP=False


def stop(*_):
    global STOP
    STOP=True


def load_sources(root):
    path=Path(root)/"public/data"
    files=("stop-inventory.json","route-shapes.geojson","bairros-oficiais.geojson")
    return tuple(json.loads((path/file).read_text(encoding="utf-8")) for file in files)


def ingest(store, collector, inventory, shapes, area):
    run={"id":str(uuid.uuid4()),"started_at":utcnow(),"status":"running",
         "accepted":0,"rejected":0}
    store.save_run(run)
    try:
        result=collector.once(inventory,shapes,area)
        normalized=[]
        for row in result["vehicles"]:
            try:
                normalized.append(normalize_position(row))
            except (ValueError,TypeError):
                run["rejected"]+=1
        run["accepted"]=store.insert(normalized)
        for vid in {x["vehicle_id"] for x in normalized}:
            history=store.history(vehicle=vid,start=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat())
            store.save_events(history)
        run["status"]="partial" if run["rejected"] else ("reference" if normalized else "no_positions_observed")
        return run, result
    except Exception as exc:
        run["status"]="failed"
        run["message"]=type(exc).__name__  # Não registrar URL, payload ou IDs de veículos.
        return run, None
    finally:
        run["ended_at"]=utcnow()
        store.save_run(run)


def main():
    if os.getenv("GOBUS_READ_AUTHORIZED")!="true" or os.getenv("GOBUS_ACCEPT_HTTP")!="true":
        raise SystemExit("Leitura TACOM bloqueada: exige autorização e aceite explícito de HTTP sem TLS")
    interval=max(60,int(os.getenv("GOBUS_CYCLE_SECONDS","180")))
    spacing=max(15,float(os.getenv("GOBUS_REQUEST_SPACING","15")))
    root=Path(__file__).resolve().parents[2]
    private=root/"var/gobus"
    private.mkdir(parents=True,exist_ok=True)
    state_path=private/"live-state.json"
    state=json.loads(state_path.read_text()) if state_path.is_file() else {}
    inventory,shapes,area=load_sources(root)
    store=Store()
    store.initialize()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    with httpx.Client(follow_redirects=False,trust_env=False) as client:
        while not STOP:
            collector=LiveCollector(client,state=state,spacing=spacing,max_requests=16)
            run,report=ingest(store,collector,inventory,shapes,area)
            state=collector.state
            atomic_json(state_path,state)
            print(json.dumps({"event":"gobus_live_cycle","status":run["status"],
                "accepted":run["accepted"],"rejected":run["rejected"],
                "requests":collector.requests,"access_denied":collector.denied}),flush=True)
            if collector.denied:
                break
            for _ in range(interval):
                if STOP:break
                time.sleep(1)


if __name__=="__main__":
    main()
