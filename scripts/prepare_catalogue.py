"""Catálogo factual; nenhum endpoint candidato é promovido automaticamente."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'public/data';now=datetime.now(timezone.utc).isoformat()
def item(id,name,status,description,url,features):return dict(id=id,name=name,status=status,description=description,url=url,features=features,checked_at=now)
integrations=[
 item('pmtiles','Cartografia local · PMTiles','available','Arquivo vetorial local com bairros e setores reais. Linhas são incluídas apenas quando há geometria com proveniência.','https://github.com/marcianolima/webgis-transporte-canoas/blob/main/docs/MAPA-PMTILES.md',['18 bairros e 659 setores','Modo compatível sem WebGL','GeoJSON local como alternativa automática']),
 item('ngs','Sogal / NGS · programação','available','Endpoints públicos vinculados no portal da operadora; cadastro, datas, saídas e logradouros.','https://ngsservicos.com/sogal/horarios/',['Consulta por data exata','Horários e sentidos publicados','Sem comprovação de operação real']),
 item('bairros','Bairros oficiais · GeoCanoas','available','18 bairros reutilizados da base municipal já integrada ao WebGIS Empreender.','https://geo.canoas.rs.gov.br/server/rest/services/BAIRROSOFICIAL/FeatureServer',['Geometrias locais em EPSG:4326','Área calculada em EPSG:31982','Origem municipal; serviço não revalidado nesta sessão']),
 item('censo','Setores · Censo 2022','available','659 setores e população reutilizados da base local do WebGIS Empreender; referência IBGE.','https://github.com/marcianolima/webgis-empreender-canoas/tree/main/public/data',['Recorte de Canoas: código 4304606','Dados censitários, não telemetria','Sem estimativa de população atendida']),
 item('gobus','Canoas GoBus · TACOM','pending','APK GoBus 1.29.1.2 analisado estaticamente; contratos de itinerário, posições, paradas e ETA identificados. API municipal ainda não homologada.','https://play.google.com/store/apps/details?id=com.tacom.canoas.gobus',['Pacote com.tacom.canoas.gobus','APK 1.29.1.2 com host e recursos confirmados estaticamente','GPS, paradas, shapes e ETA municipais ainda não validados']),
 item('ngs-map','Mapa de itinerários · NGS','blocked','Endpoint identificado no JavaScript público respondeu HTTP 404 com linha e sentido de teste.','https://ngsservicos.com/sogal/horarios/',['getMapaJson.php?LINHA=05000&SENTIDO=01','Não desenhamos trajetos aproximados']),
 item('osm','OpenStreetMap · paradas','blocked','Consultas Overpass sem resposta utilizável neste ambiente (406 ou timeout). Nenhum ponto foi inventado.','https://www.openstreetmap.org/copyright',['Fonte colaborativa, sujeita à ODbL','Não equivale a cadastro oficial municipal']),
 item('ibge-boundary','Limite municipal · IBGE','blocked','Serviço de malhas não acessível nesta sessão (HTTP 503). Contorno disponível é a união dos bairros, identificada como derivada.','https://servicodados.ibge.gov.br/api/v3/malhas/municipios/4304606?formato=application/vnd.geo+json',['Sem homologação como limite municipal','Arquivo simplificado de outro projeto não adotado como oficial']),
 item('teu','TEU Ônibus · TACOM','pending','Aplicativo inclui redes municipais e metropolitanas. Compatibilidade com GoBus ainda não comprovada por contrato ou APK.','https://play.google.com/store/apps/details?id=com.tacom.teuonibus',['Escopo metropolitano não importado','Não misturar serviços intermunicipais'])]
methods=[
 dict(id='departures',name='Saídas programadas',formula='Contagem dos registros de saída por linha, data e sentido.',unit='saídas',requirements='Quadro da operadora para a data selecionada.',limitation='Não comprova viagem realizada; sem extrapolação para outras datas.'),
 dict(id='scheduled-headway',name='Intervalo médio programado',formula='Σ(tᵢ − tᵢ₋₁) / n, por sentido; média ponderada dos intervalos disponíveis.',unit='minutos',requirements='Duas ou mais saídas ordenadas no mesmo sentido.',limitation='Inclui todos os períodos publicados. A madrugada seguinte usa minutos de serviço acima de 1440.'),
 dict(id='headway',name='Intervalo observado e regularidade',formula='hᵢ = passagemᵢ − passagemᵢ₋₁; CV = desvio padrão populacional(h) / média(h).',unit='minutos e coeficiente sem unidade',requirements='Pelo menos 3 passagens no mesmo ponto, linha e sentido, com GPS validado.',limitation='Motor unitário implementado. Extração de passagens e associação a viagens pendentes; não usar posições brutas como passagens.'),
 dict(id='jump',name='Saltos ou inconsistências de GPS',formula='Distância geodésica GRS80 / Δt × 3,6 > 100 km/h, com 0 < Δt ≤ 180 s.',unit='km/h e segundos',requirements='Mesmo veículo, fonte e linha; timestamps de origem com fuso.',limitation='Resultado inconclusivo sobre operação; velocidade média implícita não é velocidade instantânea.'),
 dict(id='deviation',name='Possível afastamento do itinerário',formula='Distância em EPSG:31982 de duas observações consecutivas ao trajeto > 100 m, com Δt ≤ 90 s.',unit='metros',requirements='Trajeto autorizado e versão temporal válidos; duas posições confiáveis.',limitation='Teste de consistência espacial. Conferir erro GPS e desvios autorizados. Worker atual não fornece shape: regra fica sem execução operacional.'),
 dict(id='stopped',name='Interrupção prolongada de movimento',formula='Pelo menos 4 amostras, duração ≥ 600 s, intervalos ≤ 180 s, todas até 30 m da primeira.',unit='segundos e metros',requirements='Série contínua do mesmo veículo, linha e fonte.',limitation='Sinal inconclusivo; terminais, congestionamento e intervalos de serviço podem explicar a parada.'),
 dict(id='coverage',name='Cobertura espacial de área até 300 m',formula='Área(bairro ∩ união(buffer(paradas, 300 m))) / área(bairro) × 100.',unit='%',requirements='Cadastro geográfico de paradas homologado; cálculo em EPSG:31982.',limitation='Indisponível sem paradas. Distância euclidiana; não representa caminhada ou população coberta.'),
 dict(id='punctuality',name='Pontualidade e viagens realizadas',formula='Não calculada nesta versão.',unit='Não disponível',requirements='Identificação de viagens, programação oficial, observações e critérios acordados.',limitation='Ausência de GPS não comprova viagem cancelada. Associação a viagens, atrasos, antecipações e km cumpridos permanecem pendentes.')]
previous=json.loads((out/'catalogue.json').read_text()) if (out/'catalogue.json').exists() else {}
checked={x['id']:x['checked_at'] for x in previous.get('integrations',[])}
network=json.loads((out/'network.json').read_text()) if (out/'network.json').exists() else {}
for integration in integrations:
    integration['checked_at']=network.get('generated_at',now) if integration['id']=='ngs' else checked.get(integration['id'],now)
    if integration['id']=='ngs' and network.get('status')=='partial':integration['status']='partial'
(out/'catalogue.json').write_text(json.dumps({'generated_at':now,'integrations':integrations,'methodologies':methods},ensure_ascii=False,separators=(',',':')))
(out/'vehicles.json').write_text(json.dumps({'status':'unavailable','generated_at':None,'vehicles':[],'message':'Serviço GPS de Canoas aguardando validação do APK e da API operacional.'},ensure_ascii=False))
assets=[]
for name,origin in [('bairros-oficiais.geojson','GeoCanoas / BAIRROSOFICIAL'),('censo2022-setores.geojson','IBGE / WebGIS Empreender Canoas')]:
 path=out/name
 assets.append({'file':name,'source':origin,'retrieved_at':now,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'upstream_url':'https://raw.githubusercontent.com/marcianolima/webgis-empreender-canoas/main/public/data/'+name})
evidence=root/'research/cartography-evidence.json'
if not evidence.exists():evidence.write_text(json.dumps(assets,ensure_ascii=False,indent=2))
