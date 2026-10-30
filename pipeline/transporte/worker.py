"""Worker persistente para um feed NORMALIZADO expressamente homologado."""
import json
import os
import signal
import time
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import httpx
from .audit import normalize_position
from .http import utcnow
from .store import Store

STOP = False


def stop(*_):
    global STOP
    STOP = True


def once(store, client, url, token=None):
    run={'id':str(uuid.uuid4()),'started_at':utcnow(),'status':'running','accepted':0,'rejected':0}
    try:
        response=client.get(url,headers={'Authorization':'Bearer '+token} if token else {})
        response.raise_for_status()
        data=response.json()
        if not isinstance(data,dict) or not isinstance(data.get('vehicles'),list):
            raise ValueError('Contrato do feed inválido')
        accepted=[]
        for item in data['vehicles']:
            try:
                accepted.append(normalize_position(item))
            except (ValueError,TypeError):
                run['rejected']+=1
        if data['vehicles'] and not accepted:
            raise ValueError('Todos os registros foram rejeitados')
        run['accepted']=store.insert(accepted)
        # Reprocessamento incremental das últimas 2 horas por veículo observado.
        for vehicle in {p['vehicle_id'] for p in accepted}:
            history=store.history(vehicle=vehicle,start=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat())
            store.save_events(history)
        run['status']='partial' if run['rejected'] else 'success'
    except Exception as exc:
        run['status']='failed'
        # Não gravar URLs, headers ou mensagens remotas que possam conter segredos.
        run['message']=type(exc).__name__
    run['ended_at']=utcnow()
    store.save_run(run)
    print(json.dumps({'event':'collection',**run}),flush=True)
    return run


def main():
    url=os.getenv('GPS_FEED_URL','')
    if os.getenv('SOURCE_HOMOLOGATED')!='true':
        raise SystemExit('Fonte não homologada: worker permanece desativado')
    parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query:
        raise SystemExit('Feed requer HTTPS e URL sem credenciais ou query')
    allowed=os.getenv('GPS_FEED_ALLOWED_HOST','')
    if parsed.hostname!=allowed:
        raise SystemExit('Host do feed não corresponde ao host autorizado')
    interval=max(30,int(os.getenv('GPS_INTERVAL_SECONDS','60')))
    store=Store();store.initialize()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    failures=0
    with httpx.Client(timeout=20,follow_redirects=False) as client:
        while not STOP:
            run=once(store,client,url,os.getenv('GPS_FEED_TOKEN'))
            failures=failures+1 if run['status']=='failed' else 0
            delay=min(900,interval*2**min(failures,4))
            # Cada segundo permite encerramento ordenado; intervalo nunca inferior ao autorizado.
            for _ in range(delay):
                if STOP:break
                time.sleep(1)


if __name__=='__main__':
    main()
