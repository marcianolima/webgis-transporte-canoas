"""Captura autorizada, limitada, somente para dados geográficos estáticos GoBus.

Não consulta GPS, alertas, cartões nem operações com efeitos colaterais.
Cada recurso é obtido uma vez. Os arquivos permanecem em var/gobus (privado).
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
from urllib.error import HTTPError, URLError
from transporte.gobus import cities, payload, request_path

BASE = 'http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/'
ALLOWED = {'paradas_geograficas', 'itinerario'}
MAX_REQUESTS = 12

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect não autorizado')

def get(opener, kind, params=None, maximum=5_000_000):
    path = request_path(kind, **(params or {}))
    request = urllib.request.Request(BASE+path, headers={
        'Accept':'application/javascript,application/json,text/plain',
        'User-Agent':'GeoCanoasTransporte-AuthorizedResearch/0.1'})
    with opener.open(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError('HTTP diferente de 200')
        raw = response.read(maximum+1)
    if len(raw)>maximum:
        raise ValueError('Resposta acima do limite')
    parsed=payload(raw.decode('utf-8-sig'))
    return raw, parsed

def capture(plan, *, output: Path, opener=None, pause=time.sleep):
    """Captura somente recursos explicitamente solicitados em arquivo aprovado."""
    if plan.get('authorized') is not True or plan.get('allow_plain_http') is not True:
        raise ValueError('Exige autorização e reconhecimento do HTTP sem TLS')
    if plan.get('city') != 'CAN':
        raise ValueError('Cidade CAN obrigatória e precisa ser confirmada pela fonte')
    resources=plan.get('resources')
    if not isinstance(resources,list) or not 1<=len(resources)<=MAX_REQUESTS:
        raise ValueError('Plano deve ter entre 1 e 12 consultas explícitas')
    requests=[]
    seen=set()
    for item in resources:
        if not isinstance(item,dict) or item.get('kind') not in ALLOWED:
            raise ValueError('Consulta não permitida no plano')
        kind=item['kind']
        key='linha' if kind=='paradas_geograficas' else 'itinerario'
        params={key:item.get(key),'cidade':'CAN'}
        path=request_path(kind,**params)
        if path in seen:
            raise ValueError('Requisição repetida no plano')
        seen.add(path)
        requests.append((kind,key,str(item[key]),params))
    opener=opener or urllib.request.build_opener(NoRedirect)
    city_raw,city_data=get(opener,'cidades')
    if not any(x['code']=='CAN' and 'CANOAS' in x['name'].upper()
               for x in cities(city_raw.decode('utf-8-sig'))):
        raise ValueError('A fonte não confirmou CAN/Canoas; nenhuma captura realizada')
    # Uma consulta a cidadesApp mais as <=12 consultas geográficas.
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    captured=[]
    for kind,key,identifier,params in requests:
        pause(3)
        raw,data=get(opener,kind,params)
        digest=hashlib.sha256(raw).hexdigest()
        file=f'{kind}-{identifier}-{digest[:10]}.jsonp'
        path=output/file
        if not path.exists():
            path.write_bytes(raw)
        captured.append({'kind':kind,key:identifier,'file':file,'sha256':digest,
                         'bytes':len(raw),'success':data.get('sucesso') is True})
    report={'city':'CAN','captured_at':datetime.now(timezone.utc).isoformat(),
            'source':'TACOM-GoBus', 'source_protocol':'HTTP-unencrypted',
            'authorization_asserted':True,'records':captured,
            'published':False,'note':'Staging somente; não valida correspondência SIU↔NGS.'}
    (output/'capture-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('plan',type=Path,help='Plano explícito JSON com até 12 consultas')
    cli.add_argument('--output',type=Path,default=Path('var/gobus/captures'))
    args=cli.parse_args()
    plan=json.loads(args.plan.read_text(encoding='utf-8'))
    result=capture(plan,output=args.output)
    print(json.dumps({'city':result['city'],'records':len(result['records']),
                      'status':'captured_private_not_published'},ensure_ascii=False))

if __name__=='__main__':
    main()
