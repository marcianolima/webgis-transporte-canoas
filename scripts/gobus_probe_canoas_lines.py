"""Confere catálogo de linhas Canoas (codcid) com NGS, sem publicar dados.

Duas consultas de metadados; códigos exibidos são apenas CANDIDATOS.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path
from transporte.gobus import lines,line_cities,request_path
from scripts.gobus_probe_catalogue import fetch,BASE,NoRedirect

def get_citylines(opener):
    request=urllib.request.Request(BASE+request_path('cidades_linhas',cidade='MPA'),
        headers={'User-Agent':'GeoCanoasTransporte-AuthorizedResearch/0.1'})
    with opener.open(request,timeout=15) as response:
        raw=response.read(1_000_001)
        if len(raw)>1_000_000: raise ValueError('Resposta grande')
    return line_cities(raw.decode('utf-8-sig'))

def survey(opener, network, pause=time.sleep):
    city_codes=[r['city_id'] for r in get_citylines(opener) if r['name'].upper().strip()=='CANOAS']
    if len(city_codes)!=1:
        raise ValueError('Código numérico de Canoas indisponível')
    city_id=city_codes[0]
    pause(2)
    source=lines(fetch(opener,'linhas'))
    municipal=[r for r in source if str(r.get('codcid'))==city_id and r.get('praca')=='MPA']
    official={str(r['id']).lstrip('0') or '0' for r in network.get('routes',[])}
    candidates=[r for r in municipal if (str(r.get('sgl','')).lstrip('0') or '0') in official]
    # Um código exato não prova que o serviço, sentido e variante sejam equivalentes.
    return {'source_city_group':'MPA','verified_city_name':'CANOAS',
        'verified_city_code':city_id,
        'source_total_lines':len(source),'canoas_source_lines':len(municipal),
        'ngs_catalogue_lines':len(official),'exact_code_candidate_matches':len(candidates),
        'examples_candidate_line_codes':[r.get('sgl') for r in candidates[:12]],
        'crosswalk_status':'candidate_only_manual_review_required',
        'gps_collected':False,'geometries_collected':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autorizado',action='store_true')
    p.add_argument('--aceito-http',action='store_true')
    p.add_argument('--network',type=Path,default=Path('public/data/network.json'))
    args=p.parse_args()
    if not args.autorizado or not args.aceito_http:
        p.error('Exige autorização de acesso e ciência de HTTP legado')
    network=json.loads(args.network.read_text(encoding='utf-8'))
    print(json.dumps(survey(urllib.request.build_opener(NoRedirect),network),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
