"""Captura explícita e autorizada de geometrias GoBus, sem GPS ou alarmes.

A praça de consulta é MPA; Canoas é o município codcid=4, confirmado em
V3/cidadesLinhas/MPA. Capturas privadas em var/gobus, com hash e proveniência.
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
from transporte.gobus import line_cities, lines, payload, request_path

BASE = 'http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/'
ALLOWED = {'paradas_geograficas', 'itinerario'}
MAX_REQUESTS = 12

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect não autorizado')

def get(opener, kind, params=None, maximum=5_000_000):
    path=request_path(kind,**(params or {}))
    request=urllib.request.Request(BASE+path,headers={
        'Accept':'application/javascript,application/json,text/plain',
        'User-Agent':'GeoCanoasTransporte-AuthorizedResearch/0.1'})
    with opener.open(request,timeout=20) as response:
        if response.status!=200:
            raise ValueError('HTTP diferente de 200')
        raw=response.read(maximum+1)
    if len(raw)>maximum:
        raise ValueError('Resposta acima do limite')
    parsed=payload(raw.decode('utf-8-sig'))
    return raw,parsed

def capture(plan, *, output: Path, opener=None, pause=time.sleep):
    if plan.get('authorized') is not True or plan.get('allow_plain_http') is not True:
        raise ValueError('Exige autorização e reconhecimento do HTTP sem TLS')
    if plan.get('city')!='MPA' or str(plan.get('canoas_city_id',''))!='4':
        raise ValueError('Praça de origem MPA e cidade codcid=4 obrigatórias')
    if plan.get('municipality_code')!='4304606':
        raise ValueError('Escopo exclusivo Canoas 4304606')
    resources=plan.get('resources')
    if not isinstance(resources,list) or not 1<=len(resources)<=MAX_REQUESTS:
        raise ValueError('Plano exige entre 1 e 12 consultas explícitas')
    requests=[]
    seen=set()
    for item in resources:
        if not isinstance(item,dict) or item.get('kind') not in ALLOWED:
            raise ValueError('Consulta não permitida no plano')
        kind=item['kind']
        key='linha' if kind=='paradas_geograficas' else 'itinerario'
        params={key:item.get(key),'cidade':'MPA'}
        path=request_path(kind,**params)
        if path in seen: raise ValueError('Requisição repetida')
        seen.add(path)
        if kind=='itinerario':
            relation=str(item.get('siu_line_id',''))
            if not relation.isdecimal() or item.get('relation_approved') is not True:
                raise ValueError('Itinerário requer linha SIU associada e relação aprovada')
        else:
            relation=str(item[key])
        requests.append((kind,key,str(item[key]),relation,params))
    opener=opener or urllib.request.build_opener(NoRedirect)
    city_raw,_=get(opener,'cidades_linhas',{'cidade':'MPA'})
    identified=[c['city_id'] for c in line_cities(city_raw.decode('utf-8-sig'))
                if c['name'].upper().strip()=='CANOAS']
    if identified!=['4']:
        raise ValueError('A TACOM não confirmou codcid=4 para Canoas')
    pause(2)
    lines_raw,_=get(opener,'linhas')
    local={str(r['cod']):r for r in lines(lines_raw.decode('utf-8-sig'))
           if str(r.get('codcid'))=='4' and r.get('praca')=='MPA'}
    if not local:
        raise ValueError('Nenhuma linha CANOA codcid=4 encontrada')
    for kind,key,identifier,relation,params in requests:
        if relation not in local:
            raise ValueError('Linha SIU fora do cadastro municipal validado: '+relation)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)

    def save(kind,id,raw):
        digest=hashlib.sha256(raw).hexdigest()
        filename=f'{kind}-{id}-{digest[:10]}.jsonp'
        target=output/filename
        if not target.exists():target.write_bytes(raw)
        return {'kind':kind,'file':filename,'sha256':digest,'bytes':len(raw)}
    cities_evidence=save('cidades_linhas','MPA',city_raw)
    lines_evidence=save('linhas','MPA',lines_raw)
    captured=[]
    for kind,key,identifier,relation,params in requests:
        pause(3)
        raw,_=get(opener,kind,params)
        item=save(kind,identifier,raw)
        item.update({key:identifier,'siu_line_id':relation})
        captured.append(item)
    report={'source_city_group':'MPA','canoas_city_id':'4',
            'municipality_code':'4304606',
            'captured_at':datetime.now(timezone.utc).isoformat(),
            'source':'TACOM-GoBus', 'source_protocol':'HTTP-unencrypted',
            'authorization_asserted':True,
            'source_cities':cities_evidence,'source_lines':lines_evidence,
            'municipal_source_lines':len(local),'records':captured,
            'published':False,
            'note':'Captura privada. Itinerários/linhas NGS requerem conferência e aprovação.'}
    (output/'capture-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('plan',type=Path)
    cli.add_argument('--output',type=Path,default=Path('var/gobus/captures'))
    args=cli.parse_args()
    result=capture(json.loads(args.plan.read_text(encoding='utf-8')),output=args.output)
    print(json.dumps({'municipality_code':result['municipality_code'],
                      'municipal_source_lines':result['municipal_source_lines'],
                      'records':len(result['records']),
                      'status':'captured_private_not_published'},ensure_ascii=False))

if __name__=='__main__':
    main()
