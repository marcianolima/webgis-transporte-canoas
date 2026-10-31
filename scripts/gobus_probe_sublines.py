"""Sonda controlada das sublinhas TACOM de uma linha municipal confirmada.

Três GET de leitura; relatório apenas quantidade/nomes de campos, sem payload.
"""
import argparse
import json
import time
import urllib.request
from transporte.gobus import lines,line_cities,payload
from scripts.gobus_capture_geography import get,NoRedirect

def sample(opener,pause=time.sleep,code='05006'):
    raw,_=get(opener,'cidades_linhas',{'cidade':'MPA'})
    matches=[r for r in line_cities(raw.decode('utf-8-sig')) if r['name'].upper().strip()=='CANOAS']
    if len(matches)!=1 or matches[0]['city_id']!='4':
        raise ValueError('Canoas não confirmada')
    pause(2)
    raw,_=get(opener,'linhas')
    matches=[r for r in lines(raw.decode('utf-8-sig')) if r.get('praca')=='MPA'
             and str(r.get('codcid'))=='4' and str(r.get('sgl','')).lstrip('0')==code.lstrip('0')]
    if len(matches)!=1:
        raise ValueError('Código de linha municipal não unívoco')
    source_id=str(matches[0]['cod'])
    pause(3)
    raw,data=get(opener,'sublinhas',{'linha':source_id,'cidade':'MPA'})
    # Relata somente estrutura; campos de sublinha podem ter identificação própria.
    items=data.get('subLinhas',[])
    return {'source_city':'MPA','canoas_city_id':'4','sample_route_code':code,
            'response_fields':sorted(data.keys()),'sublines_type':type(items).__name__,
            'sublines_count':len(items) if isinstance(items,list) else None,
            'first_sublinha_fields':sorted(items[0]) if isinstance(items,list) and items and isinstance(items[0],dict) else [],
            'gps_collected':False,'itinerary_id_assumed':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autorizado',action='store_true')
    p.add_argument('--aceito-http',action='store_true')
    args=p.parse_args()
    if not args.autorizado or not args.aceito_http:
        p.error('Autorização e ciência de HTTP sem TLS exigidas')
    print(json.dumps(sample(urllib.request.build_opener(NoRedirect)),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
