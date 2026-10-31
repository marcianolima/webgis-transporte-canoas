"""Sonda independente de uma leitura do catálogo geral de linhas SIU/TACOM.

O retorno NÃO é considerado municipal sem confirmação de cidade. Sem GPS.
"""
import argparse
import json
import sys
import urllib.request
from urllib.error import HTTPError, URLError
from collections import Counter
from transporte.gobus import lines
from scripts.gobus_probe_catalogue import fetch, NoRedirect

def run(opener):
    raw=fetch(opener,'linhas')
    rows=lines(raw)
    city_codes=Counter(str(r.get('praca') or '(ausente)') for r in rows)
    codes=Counter(str(r.get('codcid') or '(ausente)') for r in rows)
    return {'source':'TACOM-GoBus-configured-legacy-host',
            'response_valid':True,'source_line_count':len(rows),
            'praca_counts':dict(sorted(city_codes.items())[:25]),
            'codcid_distinct':len(codes),'explicit_CAN_count':city_codes.get('CAN',0),
            'municipal_scope_confirmed':False,'gps_collected':False,
            'note':'Nenhum código é atribuído a Canoas sem vínculo municipal validado.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autorizado',action='store_true')
    p.add_argument('--aceito-http',action='store_true')
    args=p.parse_args()
    if not args.autorizado or not args.aceito_http:
        p.error('Exige autorização e reconhecimento de transporte HTTP legado')
    try:
        print(json.dumps(run(urllib.request.build_opener(NoRedirect)),ensure_ascii=False,indent=2))
    except (HTTPError,URLError,ValueError,TimeoutError,OSError,UnicodeError) as exc:
        print(json.dumps({'status':'unverified','error_type':type(exc).__name__,
                          'source_line_count':None},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2) from None

if __name__=='__main__':
    main()
