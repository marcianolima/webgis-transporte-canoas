"""Análises métricas com SIRGAS 2000 / UTM 22S, nunca em graus."""
import json
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform, unary_union
from shapely import make_valid
from .http import utcnow
from .collect import dump

PROJECT = Transformer.from_crs(4326, 31982, always_xy=True).transform
UNPROJECT = Transformer.from_crs(31982, 4326, always_xy=True).transform


def valid_coordinate(lon, lat, local=True):
    if isinstance(lon, bool) or isinstance(lat, bool):
        return False
    try:
        lon, lat = float(lon), float(lat)
        return (-51.40 <= lon <= -50.95 and -30.12 <= lat <= -29.65) if local else (-180 <= lon <= 180 and -90 <= lat <= 90)
    except (TypeError, ValueError):
        return False


def prepare(root):
    public = Path(root) / 'public/data'
    neighborhoods = json.loads((public / 'bairros-oficiais.geojson').read_text())
    polygons = [make_valid(shape(f['geometry'])) for f in neighborhoods['features']]
    if len(polygons) != 18 or not all(p.is_valid and p.area > 0 for p in polygons):
        raise ValueError('Base de bairros não atende à validação esperada')
    boundary = unary_union(polygons)
    dump(public / 'boundary.geojson', {'type': 'FeatureCollection', 'features': [{'type': 'Feature',
        'properties': {'name': 'União dos bairros oficiais', 'is_official_municipal_boundary': False,
                       'source': 'BAIRROSOFICIAL / GeoCanoas', 'method': 'union-neighborhoods-v1'}, 'geometry': mapping(boundary)}]})
    stops_path = public / 'stops.geojson'
    if not stops_path.exists():
        dump(stops_path, {'type': 'FeatureCollection', 'features': [], 'status': 'unavailable',
            'description': 'Nenhum cadastro de paradas geográficas homologado nesta publicação.'})
    stops = json.loads(stops_path.read_text())
    points = [transform(PROJECT, shape(f['geometry'])) for f in stops['features'] if shape(f['geometry']).geom_type == 'Point']
    buffer = unary_union([p.buffer(300) for p in points]) if points else None
    analysis = []
    for feature, polygon in zip(neighborhoods['features'], polygons):
        p = feature['properties']
        metric = transform(PROJECT, polygon)
        area = metric.area / 1e6
        count = sum(metric.covers(point) for point in points) if points else None
        analysis.append({'name': p['BAIRRO'], 'area_km2': round(area, 6), 'population': p.get('POPULACAO_2022'),
            'stops': count, 'stops_per_km2': round(count / area, 4) if count is not None else None,
            'covered_area_pct': round(metric.intersection(buffer).area / metric.area * 100, 3) if buffer is not None else None})
    sectors = json.loads((public / 'censo2022-setores.geojson').read_text())
    if not all(str(f['properties'].get('id', '')).startswith('4304606') for f in sectors['features']):
        raise ValueError('Setores fora do município')
    # O arquivo de referência mantém só os atributos necessários para o mapa e análise.
    slim = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': f['geometry'],
        'properties': {k: f['properties'].get(k) for k in ('id','urban','bairro_ibge','area_km2','pop')}} for f in sectors['features']]}
    dump(public / 'censo2022-setores.geojson', slim)
    dump(public / 'territory.json', {'generated_at': utcnow(), 'neighborhoods': sorted(analysis, key=lambda x: x['name']),
        'stops_status': 'reference' if points else 'unavailable',
        'stops_source': ', '.join(sorted({str(f.get('properties',{}).get('source','não informado')) for f in stops['features']})) if points else None,
        'sectors': len(sectors['features']), 'limitations': [
        'O contorno da união de bairros não está homologado como limite municipal oficial.',
        'Os setores censitários e seus atributos foram reutilizados da base local do WebGIS Empreender; referência IBGE 2022.',
        'Cobertura euclidiana de área não é distância pela rede de pedestres nem percentual de população atendida.',
        'Cadastro de paradas e associação às linhas municipais dependem de homologação.',
        'Extensão de linhas, acessibilidade a equipamentos e oferta por bairro aguardam trajetos e paradas validados.']})
    return analysis


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[2])
