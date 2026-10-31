"""Inventário offline TACOM/NGS para revisão humana de códigos, sem autoaprovação.

Consumir respostas JSONP guardadas sob var/gobus por operador autorizado.
Não consultar rede e não importar trajetos/veículos automaticamente.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from .gobus import line_cities, lines

def normalized(value):
    value=str(value or '').strip()
    return value.lstrip('0') or '0'

def propose(city_raw: str, line_raw: str, ngs_network: dict) -> dict:
    matched_cities=[r['city_id'] for r in line_cities(city_raw)
                    if r['name'].strip().upper()=='CANOAS']
    if matched_cities!=['4']:
        raise ValueError('Canoas/codcid4 não confirmado pela resposta TACOM')
    source=[r for r in lines(line_raw) if r.get('praca')=='MPA' and str(r.get('codcid'))=='4']
    official=ngs_network.get('routes')
    if not isinstance(official,list):
        raise ValueError('Catálogo NGS inválido')
    by_code={}
    for r in official:
        code=normalized(r.get('code',r.get('id')))
        by_code.setdefault(code,[]).append(r)
    rows=[]
    seen=set()
    for row in source:
        code=normalized(row['sgl'])
        matches=by_code.get(code,[])
        key=str(row['cod'])
        if key in seen:raise ValueError('ID de linha duplicado no catálogo TACOM')
        seen.add(key)
        rows.append({
            'siu_line_id':key,'siu_route_code':str(row['sgl']),
            'siu_route_name':str(row['nom']),
            'ngs_route_id':str(matches[0]['id']) if len(matches)==1 else '',
            'ngs_route_name':str(matches[0].get('name','')) if len(matches)==1 else '',
            'match_status':'candidate_exact_code' if len(matches)==1 else
                           ('ambiguous_ngs_code' if matches else 'not_matched'),
            'crosswalk_approved':'false',
            'direction_review':'pending',
            'variant_review':'pending',
            'validity_review':'pending'
        })
    return {'municipality_code':'4304606','source_city_code':'4','source_city_group':'MPA',
            'status':'review_only','source_line_count':len(source),
            'candidate_count':sum(x['match_status']=='candidate_exact_code' for x in rows),
            'unmatched_count':sum(x['match_status']=='not_matched' for x in rows),
            'rows':rows}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cidades',type=Path,required=True)
    p.add_argument('--linhas',type=Path,required=True)
    p.add_argument('--network',type=Path,default=Path('public/data/network.json'))
    p.add_argument('--output',type=Path,default=Path('var/gobus/revisao-crosswalk.csv'))
    a=p.parse_args()
    if a.cidades.stat().st_size>2_000_000 or a.linhas.stat().st_size>5_000_000:
        raise ValueError('Entrada excede limites de tamanho')
    data=propose(a.cidades.read_text(encoding='utf-8-sig'),
                 a.linhas.read_text(encoding='utf-8-sig'),
                 json.loads(a.network.read_text(encoding='utf-8')))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',encoding='utf-8-sig',newline='') as f:
        columns=list(data['rows'][0]) if data['rows'] else []
        if not columns:raise ValueError('Nenhuma linha municipal retornada')
        writer=csv.DictWriter(f,fieldnames=columns,delimiter=';')
        writer.writeheader()
        for row in data['rows']:
            # Protege CSV de execução de fórmulas ao abrir em planilhas.
            safe={k:("'"+v if v.startswith(('=','+','-','@')) else v)
                  for k,v in row.items()}
            writer.writerow(safe)
    print(json.dumps({k:v for k,v in data.items() if k!='rows'}|{'file':str(a.output)},ensure_ascii=False))

if __name__=='__main__':
    main()
