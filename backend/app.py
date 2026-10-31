import base64
import csv
import io
import json
import os
import secrets
import uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path
from collections import defaultdict, deque
from threading import Lock
import time
from ipaddress import ip_address, ip_network
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transporte.store import Store
from transporte.http import utcnow
from transporte.audit import timestamp


def create_app(store=None):
    app=FastAPI(title='Transporte Canoas · API operacional',version='0.1.0',docs_url=None,redoc_url=None,openapi_url=None)
    db=store or Store();db.initialize()
    request_times = defaultdict(deque)
    request_lock = Lock()
    public_limit = max(1, min(10000, int(os.getenv('PUBLIC_API_LIMIT_PER_MINUTE','60'))))
    # Proxy confiável SOMENTE por CIDR explícito: não aceitar X-Real-IP de clientes diretos.
    proxy_networks = [ip_network(x.strip(), strict=False)
                      for x in os.getenv('TRUSTED_PROXY_CIDRS','').split(',')
                      if x.strip()]
    origins=[v.strip() for v in os.getenv('PUBLIC_ORIGINS','https://marcianolima.github.io').split(',') if v.strip()]
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET'],allow_headers=[],allow_credentials=False)

    def authorized(authorization:str|None=Header(default=None)):
        configured=os.getenv('ADMIN_API_KEY','')
        if len(configured)<32:
            raise HTTPException(503,'Acesso administrativo não configurado')
        provided=''
        if authorization and authorization.startswith('Bearer '):
            provided=authorization[7:]
        elif authorization and authorization.startswith('Basic '):
            try:
                user,provided=base64.b64decode(authorization[6:],validate=True).decode().split(':',1)
                if user!='admin':provided=''
            except (ValueError,UnicodeDecodeError):provided=''
        if not provided or not secrets.compare_digest(provided,configured):
            raise HTTPException(401,'Autenticação necessária',headers={'WWW-Authenticate':'Basic realm="Transporte Canoas", charset="UTF-8"'})
        return 'municipal-shared-key'

    def interval(start,end):
        try:
            a,b=timestamp(start),timestamp(end)
            if b<=a or b-a>timedelta(days=7):raise ValueError()
            return a.isoformat(),b.isoformat()
        except ValueError:
            raise HTTPException(422,'Intervalo deve ter fuso e durar de 1 segundo a 7 dias')

    @app.middleware('http')
    async def security_headers(request,call_next):
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        return response

    @app.get('/v1/health')
    def health():
        with db.connection() as connection:
            row=db.execute(connection,'SELECT ended_at,status,accepted,rejected,message FROM collection_run ORDER BY started_at DESC LIMIT 1').fetchone()
        diagnostics={}
        if row:
            try:
                summary=json.loads(row['message'] or '{}')
                permitted={'sampled_stops','active_itineraries','queried_itineraries',
                           'requests','cache_hits','failures','access_denied',
                           'rate_limited','quota_exhausted',
                           'requests_last_hour','requests_last_day'}
                if isinstance(summary,dict):
                    diagnostics={k:v for k,v in summary.items()
                                 if k in permitted and type(v) in (int,bool)}
            except (TypeError,ValueError):
                pass
        return {
            'status':row['status'] if row else 'not_configured',
            'last_run_at':row['ended_at'] if row else None,
            'accepted_last_run':row['accepted'] if row else 0,
            'rejected_last_run':row['rejected'] if row else 0,
            'source_diagnostics':diagnostics, 'time':utcnow(),
            'limitation':'A ausência de GPS não prova cancelamento nem infração.'
        }

    def vehicle_limit(request: Request):
        # Defesa em profundidade; proxy Nginx aplica a limitação distribuída.
        # Somente endereço de conexão, nunca X-Forwarded-For arbitrário.
        identity = request.client.host if request.client else 'unknown'
        if proxy_networks:
            try:
                remote = ip_address(identity)
                if any(remote in net for net in proxy_networks):
                    forwarded = request.headers.get('x-real-ip', '')
                    identity = str(ip_address(forwarded))
            except ValueError:
                # Não confiar em cabeçalhos sem origem explicitamente autorizada.
                pass
        now = time.monotonic()
        with request_lock:
            window = request_times[identity]
            while window and now-window[0] >= 60:
                window.popleft()
            if len(window) >= public_limit:
                raise HTTPException(429,'Muitas consultas de veículos',headers={'Retry-After':'60'})
            window.append(now)
            # Evitar crescimento ilimitado da tabela de IPs em serviço público.
            if len(request_times) > 20000:
                for key in list(request_times):
                    if not request_times[key] or now-request_times[key][-1] >= 60:
                        request_times.pop(key, None)

    @app.get('/v1/vehicles')
    def vehicles(request: Request, _limit=Depends(vehicle_limit)):
        # A homologação técnica não substitui autorização de divulgação pública.
        # Exigir SEMPRE o opt-in explícito e independente.
        public_allowed = os.getenv('PUBLIC_POSITIONS_ENABLED') == 'true'
        if not public_allowed:
            return {
                'status':'unavailable', 'generated_at':None, 'vehicles':[],
                'message':'Publicação de posições não autorizada; sem inferência de viagens ou cancelamentos.'
            }
        now=datetime.now(timezone.utc)
        values=db.latest((now-timedelta(minutes=3)).isoformat())
        values=[p for p in values if
                timestamp(p['observed_at']) <= now+timedelta(seconds=30) and
                p.get('municipality_code') == '4304606' and
                p.get('scope') == 'municipal']
        complete = os.getenv('SOURCE_HOMOLOGATED') == 'true'
        fields=('vehicle_id','route_id','longitude','latitude','observed_at','fetched_at',
                'source_observed_at','time_basis','signal_status','stale_polls',
                'source_itinerary_id','route_relation','bearing_basis',
                'speed_kmh','bearing','source_id')
        # Nunca declarar telemetria homologada quando faltam timestamps GPS nativos.
        fully_homologated = complete and all(
            p.get('time_basis', 'source_gps') == 'source_gps' and
            p.get('source_observed_at') for p in values
        )
        status='available' if fully_homologated else 'reference'
        return {
            'status':status,
            'generated_at':max((p.get('fetched_at') or p['observed_at'] for p in values),default=None),
            'vehicles':[{k:p.get(k) for k in fields} for p in values],
            'message':('Posições por consulta à TACOM, sem timestamp GPS de origem; '
                       'linhas/itinerários de referência, não homologação operacional.'
                       if status=='reference' else
                       'Posições observadas; registros acima de 3 minutos são omitidos.')
        }

    @app.get('/internal/positions',dependencies=[Depends(authorized)])
    def history(start:str,end:str,vehicle:str|None=None,route:str|None=None,limit:int=Query(10000,ge=1,le=50000)):
        a,b=interval(start,end)
        values=db.history(vehicle=vehicle,route=route,start=a,end=b,limit=limit+1)
        return {'data':values[:limit],'truncated':len(values)>limit,'limit':limit,'start':a,'end':b}

    @app.get('/internal/events',dependencies=[Depends(authorized)])
    def events(start:str,end:str,vehicle:str|None=None,route:str|None=None):
        a,b=interval(start,end)
        return {'data':db.events(vehicle,route,a,b)}

    @app.get('/internal/export',dependencies=[Depends(authorized)])
    def export(start:str,end:str,format:str='csv',vehicle:str|None=None,route:str|None=None):
        a,b=interval(start,end)
        values=db.history(vehicle=vehicle,route=route,start=a,end=b,limit=50001)
        if len(values)>50000:raise HTTPException(413,'Recorte acima de 50 mil registros; reduza o período')
        if format=='geojson':
            body={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[p['longitude'],p['latitude']]},'properties':{k:v for k,v in p.items() if k not in ('longitude','latitude')}} for p in values]}
            return Response(json.dumps(body,ensure_ascii=False),media_type='application/geo+json',headers={'Content-Disposition':'attachment; filename="posicoes.geojson"'})
        if format!='csv':raise HTTPException(422,'Formato permitido: csv ou geojson')
        stream=io.StringIO();fields=['source_id','vehicle_id','route_id','observed_at','fetched_at','longitude','latitude','speed_kmh','bearing']
        writer=csv.DictWriter(stream,fieldnames=fields,delimiter=';');writer.writeheader()
        for p in values:
            writer.writerow({k:("'"+str(p[k]) if isinstance(p.get(k),str) and p[k].startswith(('=','+','-','@')) else p.get(k,'')) for k in fields})
        return Response('\ufeff'+stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="posicoes.csv"'})

    class Review(BaseModel):
        classification:str=Field(pattern='^(confirmed|probable|inconclusive)$')
        reason:str=Field(min_length=20,max_length=5000)

    @app.post('/internal/events/{event_id}/reviews')
    def review(event_id:str,body:Review,actor=Depends(authorized)):
        with db.connection() as connection:
            event=db.execute(connection,'SELECT id FROM audit_event WHERE id=?',(event_id,)).fetchone()
            if not event:raise HTTPException(404,'Ocorrência não encontrada')
            identity=str(uuid.uuid4())
            db.execute(connection,'INSERT INTO audit_review VALUES (?,?,?,?,?,?)',(identity,event_id,utcnow(),actor,body.classification,body.reason))
        return {'id':identity,'event_id':event_id,'classification':body.classification,'actor':actor}

    @app.get('/admin',response_class=HTMLResponse,dependencies=[Depends(authorized)])
    def admin():
        return (Path(__file__).parent/'admin.html').read_text()
    return app
