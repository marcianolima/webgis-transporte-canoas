"""Contratos de leitura inferidos do APK Canoas GoBus 1.29.1.2.

Adaptador apenas de parsing e preparação offline. Não autoriza coleta, não comprova
escopo municipal e não promove telemetria não homologada à base operacional.
"""
from __future__ import annotations
import re
from typing import Any
from .parsing import legacy_rows, parse_jsonp

# Só GET informativo; endpoints PNE, alertas e logs intencionalmente excluídos.
PATHS = {
    'cidades': ('cidadesApp/retornoJSONCidades', ()),
    'linhas': ('buscarLinhas/retornoJSONListaLinhas', ()),
    'cidades_linhas': ('V3/cidadesLinhas/{cidade}/retornoJSONCidadesLinhas', ('cidade',)),
    'sublinhas': ('V3/retornaSublinhasDaLinha/{linha}/0/{cidade}/retornoSublinhasJSON', ('linha', 'cidade')),
    'parada_detalhes': ('buscarDadosParada/{parada}/0/retornoJSONPontosItinerario', ('parada',)),
    'paradas_linha': ('V3/buscarParadasPorLinha/{linha}/0/{cidade}/retornoJSON', ('linha', 'cidade')),
    'paradas_geograficas': ('V3/buscarParadasPorLinhaComCoordenadas/{linha}/0/{cidade}/retornoJSONH', ('linha', 'cidade')),
    'itinerario': ('V3/buscarItinerario/{itinerario}/0/{cidade}/retornoJSONItinerario', ('itinerario', 'cidade')),
    'veiculos': ('V3/retornaVeiculosMapa/{itinerario}/0/{cidade}/retornoJSONVeiculos', ('itinerario', 'cidade')),
    'previsoes': ('V3/buscarPrevisoes/{parada}/{acessivel}/0/{cidade}/retornoJSON', ('parada', 'acessivel', 'cidade')),
    'horarios': ('V3/retornaQroLinha/{linha}/0/{cidade}/retornoJSON', ('linha', 'cidade')),
    'paradas_proximas': ('V3/buscarParadasProximas/{longitude}/{latitude}/0/{cidade}/retornoJSONH', ('longitude', 'latitude', 'cidade')),
}

def request_path(kind: str, **params: Any) -> str:
    """Monta caminho validado, sem origem HTTP nem execução de rede."""
    if kind not in PATHS:
        raise ValueError('Recurso não permitido')
    template, expected = PATHS[kind]
    if set(params) != set(expected):
        raise ValueError('Parâmetros não correspondem ao contrato')
    clean: dict[str, str] = {}
    for name, value in params.items():
        v = str(value)
        if name == 'cidade':
            if not re.fullmatch(r'[A-Z]{2,12}', v):
                raise ValueError('Cidade inválida')
        elif name == 'acessivel':
            if v not in ('true', 'false'):
                raise ValueError('Acessibilidade inválida')
        elif name in ('latitude', 'longitude'):
            try:
                numeric = float(v)
            except (ValueError, TypeError):
                raise ValueError('Coordenada inválida') from None
            if not (-90 <= numeric <= 90 if name == 'latitude' else -180 <= numeric <= 180):
                raise ValueError('Coordenada fora do intervalo')
            v = str(numeric)
        elif not re.fullmatch(r'\d{1,16}', v):
            raise ValueError('Identificador inválido')
        clean[name] = v
    return template.format(**clean)

def payload(raw: str) -> dict[str, Any]:
    data = parse_jsonp(raw)
    if not isinstance(data, dict) or data.get('sucesso') is not True:
        raise ValueError('Resposta sem sucesso ou contrato inválido')
    return data

def lines(raw: str) -> list[dict[str, Any]]:
    data = payload(raw)
    source = legacy_rows(data.get('linhas'))
    result = []
    for item in source:
        if not all(str(item.get(k, '')).strip() for k in ('cod', 'sgl', 'nom')):
            raise ValueError('Linha sem identificadores/nome')
        result.append({k: item.get(k) for k in ('cod', 'sgl', 'nom', 'codcid', 'praca') if k in item})
    return result

def coordinate(longitude: Any, latitude: Any) -> tuple[float, float]:
    """Na API, x/coordX é longitude e y/coordY é latitude."""
    try:
        x = float(str(longitude).replace(',', '.'))
        y = float(str(latitude).replace(',', '.'))
    except (ValueError, TypeError):
        raise ValueError('Coordenada não numérica') from None
    if not (-180 <= x <= 180 and -90 <= y <= 90):
        raise ValueError('Coordenada fora do intervalo')
    return x, y

def stops(raw: str) -> list[dict[str, Any]]:
    data = payload(raw)
    result = []
    for item in data.get('paradas', []):
        if not isinstance(item, dict) or 'cod' not in item:
            raise ValueError('Parada inválida')
        record = {'stop_id': str(item['cod']), 'label': item.get('desc') or item.get('end'), 'siu': item.get('siu')}
        if 'x' in item and 'y' in item:
            record['longitude'], record['latitude'] = coordinate(item['x'], item['y'])
        if 'sent' in item:
            record['sentido'] = item['sent']
        if 'azimute' in item:
            record['azimute'] = item['azimute']
        result.append(record)
    return result

def itinerary(raw: str, itinerary_id: str) -> dict[str, Any]:
    data = payload(raw)
    coords = data.get('itinerarios')
    if not isinstance(coords, list) or len(coords) < 2:
        raise ValueError('Traçado incompleto')
    geometry = []
    for row in coords:
        if not isinstance(row, dict):
            raise ValueError('Vértice inválido')
        geometry.append(list(coordinate(row.get('coordX'), row.get('coordY'))))
    # A relação itinerário SIU <-> linha NGS exige homologação independente.
    return {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': geometry},
            'properties': {'source': 'gobus-apk-contract', 'itinerary_id': str(itinerary_id),
                           'homologated': False}}

def vehicles(raw: str) -> list[dict[str, Any]]:
    data = payload(raw)
    source = data.get('veiculos', [])
    if not isinstance(source, list):
        raise ValueError('Lista de veículos inválida')
    result = []
    for row in source:
        if not isinstance(row, dict) or not row.get('numVeicGestor'):
            raise ValueError('Veículo sem identificador')
        lng, lat = coordinate(row.get('long'), row.get('lat'))
        result.append({'vehicle_id': str(row['numVeicGestor']), 'longitude': lng,
                       'latitude': lat, 'route_display': row.get('descricao'),
                       'direction': row.get('direcao'), 'source_vehicle_code': row.get('cod'),
                       'source_timestamp': None, 'homologated': False})
    return result

def predictions(raw: str) -> list[dict[str, Any]]:
    data = payload(raw)
    if not isinstance(data.get('previsoes'), list):
        raise ValueError('Previsões inválidas')
    return [{k: row.get(k) for k in ('sgLin','prev','numVeicGestor','codItinerario','tpAcess')}
            for row in data['previsoes'] if isinstance(row, dict) and row.get('sgLin') != 'Sem Dados']

def cities(raw: str) -> list[dict[str, str]]:
    """Valida cidades TACOM; suporta string ou lista JSON legado, sem eval."""
    source = payload(raw).get('cidade')
    values = legacy_rows(source)
    result = []
    for row in values:
        code = str(row.get('sg', '')).strip().upper()
        if code and row.get('desc'):
            result.append({'code': code, 'name': str(row['desc']).strip()})
    return result

def line_cities(raw: str) -> list[dict[str, str]]:
    """Relaciona codcid ao nome municipal informado por V3/cidadesLinhas."""
    source = payload(raw).get('cidade')
    values = legacy_rows(source)
    result = []
    for row in values:
        code = str(row.get('cod', '')).strip()
        name = str(row.get('desc', '')).strip()
        if code.isdecimal() and name:
            result.append({'city_id': code, 'name': name})
    return result
