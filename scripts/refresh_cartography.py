"""Atualização MANUAL, explícita e validada das bases locais de referência."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from transporte.http import Fetcher
from transporte.geo import prepare
import json
root=Path(__file__).resolve().parents[1];http=Fetcher(root/'var/cartography-cache')
for name in ['bairros-oficiais.geojson','censo2022-setores.geojson']:
    url='https://raw.githubusercontent.com/marcianolima/webgis-empreender-canoas/main/public/data/'+name
    record=http.get(url,ttl=0);j=json.loads(record['body'])
    if j.get('type')!='FeatureCollection' or not j.get('features'):raise ValueError('Base vazia')
    (root/'public/data'/name).write_text(record['body'])
prepare(root)
print('Bases atualizadas. Rever evidências, metadados e diferenças antes de publicar.')
