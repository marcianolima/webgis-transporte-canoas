"""Sonda limitadíssima: duas requisições GET de catálogo GoBus; nenhum GPS.

Para uso apenas pelo operador autorizado. Não automatizar varreduras de IDs.
Os resultados publicados em logs são estatísticas, não payloads completos.
"""
import argparse
import json
import sys
import time
import urllib.request
from urllib.error import HTTPError, URLError
from transporte.gobus import lines, request_path, cities

BASE = 'http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirecionamento bloqueado')

def fetch(opener, kind):
    path=request_path(kind)
    url=BASE+path
    request=urllib.request.Request(url,headers={
        'Accept':'application/javascript,application/json,text/plain',
        'User-Agent':'GeoCanoasTransporte-AuthorizedResearch/0.1'
    })
    with opener.open(request,timeout=12) as response:
        if response.status != 200:
            raise ValueError('HTTP diferente de 200')
        body=response.read(2_000_001)
    if len(body)>2_000_000:
        raise ValueError('Resposta excessiva')
    return body.decode('utf-8-sig')

def checked_fetch(opener, kind):
    try:
        return fetch(opener, kind)
    except HTTPError as exc:
        raise ValueError(f'{kind}:http_{exc.code}') from None
    except URLError:
        raise ValueError(f'{kind}:network_error') from None
    except TimeoutError:
        raise ValueError(f'{kind}:timeout') from None
    except ValueError:
        raise ValueError(f'{kind}:redirect_or_invalid_response') from None

def discover(opener, sleep=time.sleep):
    # Limite fixo de 2 chamadas, sem redirecionamento ou repetição.
    raw_cities=checked_fetch(opener,'cidades')
    try:
        registered=cities(raw_cities)
    except (ValueError, TypeError, SyntaxError, KeyError):
        raise ValueError('cidades:invalid_schema') from None
    target=[c for c in registered if c['code']=='CAN' and 'CANOAS' in c['name'].upper()]
    if len(target)!=1:
        raise ValueError('cidades:CAN_not_confirmed')
    sleep(2)
    raw_lines=checked_fetch(opener,'linhas')
    try:
        values=lines(raw_lines)
    except (ValueError,TypeError,SyntaxError,KeyError):
        raise ValueError('linhas:invalid_schema') from None
    # Cadastro não filtrado por cidade na requisição do APK; não atribuir tudo a Canoas.
    explicitly_city=[x for x in values if x.get('praca')=='CAN']
    return {'city_verified':True,'city_code':'CAN',
            'total_source_lines':len(values),'explicit_can_lines':len(explicitly_city),
            'scope':'source-wide, not automatically municipal',
            'gps_collected':False,'routes_collected':False,'stops_collected':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autorizado',action='store_true')
    p.add_argument('--aceito-http',action='store_true')
    args=p.parse_args()
    if not args.autorizado or not args.aceito_http:
        p.error('Exige --autorizado e --aceito-http: a URL do APK não utiliza TLS')
    opener=urllib.request.build_opener(NoRedirect)
    try:
        print(json.dumps(discover(opener),ensure_ascii=False,indent=2))
    except (ValueError,HTTPError,URLError,TimeoutError,OSError,UnicodeError) as exc:
        # Sem exposição do corpo, nomes de linhas ou URLs com parâmetros.
        print(json.dumps({'status':'unverified','error_type':type(exc).__name__,
                          'diagnostic_code':str(exc) if str(exc).startswith(('cidades:','linhas:')) else 'unclassified',
                          'gps_collected':False},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2) from None

if __name__=='__main__':
    main()
