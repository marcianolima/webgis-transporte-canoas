"""Investiga somente o cadastro de cidades das linhas (MPA/CAN).

No máximo 2 GET; não consulta dados de veículos nem cria viagens.
"""
import argparse
import json
import sys
import time
import urllib.request
from urllib.error import HTTPError,URLError
from transporte.gobus import line_cities,request_path
from scripts.gobus_probe_catalogue import BASE,NoRedirect

def survey(opener,pause=time.sleep):
    summary=[]
    for city in ('MPA','CAN'):
        if summary:
            pause(2)
        path=request_path('cidades_linhas',cidade=city)
        req=urllib.request.Request(BASE+path,headers={
            'User-Agent':'GeoCanoasTransporte-AuthorizedResearch/0.1',
            'Accept':'application/javascript,application/json,text/plain'})
        try:
            with opener.open(req,timeout=15) as response:
                if response.status!=200:
                    raise ValueError('HTTP inesperado')
                raw=response.read(1_000_001)
            if len(raw)>1_000_000:
                raise ValueError('Resposta maior que 1 MB')
            entries=line_cities(raw.decode('utf-8-sig'))
            canoas=[x for x in entries if x['name'].strip().upper()=='CANOAS']
            summary.append({'request_city':city,'valid_response':True,
                            'city_count':len(entries),
                            'canoas_city_ids':[c['city_id'] for c in canoas],
                            'city_ids_count':len({c['city_id'] for c in entries})})
            # Resultado suficiente: confirmar código numérico sem outra consulta.
            if canoas:
                break
        except (ValueError,HTTPError,URLError,TimeoutError,UnicodeError):
            summary.append({'request_city':city,'valid_response':False,
                            'city_count':None,'canoas_city_ids':[]})
    return {'source':'TACOM/GoBus legacy',
            'candidates':summary,'gps_collected':False,
            'confirmed_canoas_code': next((x['canoas_city_ids'][0] for x in summary if x['canoas_city_ids']),None),
            'note':'Código de cidade serve somente para filtrar cadastro geral; geometria/itinerário ainda não homologados.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autorizado',action='store_true')
    p.add_argument('--aceito-http',action='store_true')
    args=p.parse_args()
    if not args.autorizado or not args.aceito_http:
        p.error('Exige autorização técnica e ciência do HTTP sem TLS')
    print(json.dumps(survey(urllib.request.build_opener(NoRedirect)),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
