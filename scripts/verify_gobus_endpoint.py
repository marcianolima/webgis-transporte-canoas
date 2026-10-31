"""Sonda manual conservadora de UM endpoint SIU por execução.

Use somente com autorização do responsável pelos dados; nunca em CI/Pages.
Corpo salvo em var/, fora da publicação. Não autentica nem contorna limites.
"""
import argparse
import hashlib
import json
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from transporte.gobus import PATHS, request_path
from transporte.parsing import parse_jsonp

BASE = 'http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/'
ALLOWED = {'mpa.siumobile.com.br'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirecionamento não permitido')

def main():
    ap = argparse.ArgumentParser(description='Consulta manual de um endpoint de leitura SIU/GoBus')
    ap.add_argument('recurso', choices=tuple(PATHS))
    ap.add_argument('--autorizado', action='store_true', help='Confirmo autorização para a consulta ao fornecedor')
    ap.add_argument('--permitir-http', action='store_true', help='Host do APK usa HTTP sem TLS; risco de integridade')
    ap.add_argument('--cidade')
    ap.add_argument('--linha')
    ap.add_argument('--itinerario')
    ap.add_argument('--parada')
    ap.add_argument('--acessivel')
    ap.add_argument('--latitude')
    ap.add_argument('--longitude')
    ap.add_argument('--destino', type=Path, default=Path('var/gobus'))
    args=ap.parse_args()
    if not args.autorizado:
        ap.error('Exige --autorizado; confirme a permissão de acesso/uso dos dados')
    params={k:getattr(args,k) for k in ('cidade','linha','itinerario','parada','acessivel','latitude','longitude')
            if getattr(args,k) is not None}
    url=BASE + request_path(args.recurso,**params)
    parsed=urlsplit(url)
    if parsed.hostname not in ALLOWED or parsed.scheme not in ('http','https'):
        ap.error('Host não autorizado')
    if parsed.scheme=='http' and not args.permitir_http:
        ap.error('Fonte usa HTTP; --permitir-http aceita explicitamente o risco')
    opener=urllib.request.build_opener(NoRedirect())
    req=urllib.request.Request(url,headers={'Accept':'application/javascript,application/json,text/plain',
                                            'User-Agent':'GeoCanoasTransporte-Research/0.1'})
    with opener.open(req,timeout=15) as response:
        if response.status!=200:
            raise ValueError('HTTP não OK')
        raw=response.read(5_000_001)
        if len(raw)>5_000_000:
            raise ValueError('Resposta excede 5 MB')
    # Primeiro valide JSON/JSONP sem executar JavaScript; nunca eval.
    parsed_body=parse_jsonp(raw.decode('utf-8-sig'))
    if not isinstance(parsed_body,dict):
        raise ValueError('Payload não contém objeto')
    args.destino.mkdir(parents=True,exist_ok=True)
    fingerprint=hashlib.sha256(raw).hexdigest()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target=args.destino/f'{stamp}_{args.recurso}_{fingerprint[:10]}.jsonp'
    target.write_bytes(raw)
    # Apenas resumo, sem expor IDs, posições ou parâmetros de URL.
    print(json.dumps({'recurso':args.recurso,'sucesso':parsed_body.get('sucesso'),
                      'bytes':len(raw),'sha256':fingerprint,'arquivo':str(target),
                      'homologado':False},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
