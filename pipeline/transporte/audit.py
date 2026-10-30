"""Inferências técnicas, não infrações. Versão do algoritmo em toda ocorrência."""
import math
import statistics
from datetime import datetime, timezone
from pyproj import Geod
from shapely.geometry import Point, LineString
from shapely.ops import transform
from .geo import PROJECT, valid_coordinate

VERSION = 'audit-0.1.0'
GEOD = Geod(ellps='GRS80')


def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp exige fuso horário')
    return dt.astimezone(timezone.utc)


def normalize_position(value, now=None):
    required = ('vehicle_id','route_id','source_id','observed_at','longitude','latitude','municipality_code')
    if not isinstance(value, dict) or any(value.get(k) in (None, '') for k in required):
        raise ValueError('Posição sem identificadores obrigatórios')
    if str(value['municipality_code']) != '4304606' or value.get('scope') != 'municipal':
        raise ValueError('Registro fora do escopo municipal de Canoas')
    if not valid_coordinate(value['longitude'], value['latitude']):
        raise ValueError('Coordenada fora da área operacional esperada')
    observed = timestamp(value['observed_at'])
    now = now or datetime.now(timezone.utc)
    if (observed - now).total_seconds() > 30:
        raise ValueError('Posição no futuro')
    result = {k: value[k] for k in required} | {'scope': 'municipal', 'longitude': float(value['longitude']),
        'latitude': float(value['latitude']), 'observed_at': observed.isoformat(), 'fetched_at': now.isoformat()}
    for k, low, high in [('speed_kmh',0,180),('bearing',0,360)]:
        v = value.get(k)
        if v is not None and (not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or not low <= v <= high):
            raise ValueError(k + ' fora do domínio')
        result[k] = v
    return result


def occurrence(kind, confidence, evidence, **details):
    return {'kind': kind, 'classification': confidence, 'algorithm_version': VERSION,
            'evidence': evidence, 'details': details, 'is_infraction': False}


def trajectory_events(positions, authorized_shape=None, now=None):
    positions = sorted(positions, key=lambda p: timestamp(p['observed_at']))
    events = []
    metric_route = transform(PROJECT, LineString(authorized_shape)) if authorized_shape and len(authorized_shape)>1 else None
    for previous, current in zip(positions, positions[1:]):
        # Nunca comparar veículos/fontes diferentes nem atribuições de linha diferentes.
        if any(previous[k] != current[k] for k in ('source_id','vehicle_id','route_id')):
            continue
        seconds = (timestamp(current['observed_at']) - timestamp(previous['observed_at'])).total_seconds()
        if seconds == 0 and (previous['longitude'],previous['latitude']) != (current['longitude'],current['latitude']):
            events.append(occurrence('conflicting_position', 'inconclusive', [previous,current],
                note='Mesmo veículo e instante, coordenadas divergentes; ambas preservadas no histórico'))
        if seconds <= 0:
            continue
        _, _, meters = GEOD.inv(previous['longitude'],previous['latitude'],current['longitude'],current['latitude'])
        evidence = [{'vehicle_id': p['vehicle_id'], 'source_id': p['source_id'], 'route_id': p['route_id'],
                     'observed_at': p['observed_at'], 'longitude': p['longitude'], 'latitude': p['latitude']} for p in (previous,current)]
        speed = meters / seconds * 3.6
        if seconds <= 180 and speed > 100:
            events.append(occurrence('gps_jump', 'inconclusive', evidence, implied_speed_kmh=round(speed,2), gap_seconds=seconds,
                                     note='Pode ser erro de GPS; não comprova velocidade praticada'))
        if seconds > 180:
            events.append(occurrence('sampling_gap', 'inconclusive', evidence, gap_seconds=seconds))
        if metric_route is not None and seconds <= 90:
            distances = [transform(PROJECT, Point(p['longitude'],p['latitude'])).distance(metric_route) for p in (previous,current)]
            if min(distances)>100:
                events.append(occurrence('possible_deviation','probable',evidence,distances_m=distances,
                                         note='Conferir versão do itinerário, precisão e desvios autorizados'))
    # Parada prolongada exige >= 4 amostras, cobertura contínua e duração >= 10 min.
    for start in range(len(positions)):
        first = positions[start]
        window = [first]
        for value in positions[start+1:]:
            if any(first[k]!=value[k] for k in ('source_id','vehicle_id','route_id')):
                break
            gap=(timestamp(value['observed_at'])-timestamp(window[-1]['observed_at'])).total_seconds()
            distance=GEOD.inv(first['longitude'],first['latitude'],value['longitude'],value['latitude'])[2]
            if gap>180 or distance>30:
                break
            window.append(value)
        if len(window)>=4 and (timestamp(window[-1]['observed_at'])-timestamp(first['observed_at'])).total_seconds()>=600:
            events.append(occurrence('prolonged_stationary','inconclusive',window,
                note='Pode ocorrer em terminal, semáforo, congestionamento ou intervalo de serviço'))
            break
    return events


def headway_stats(crossings):
    """Passagens confirmadas no MESMO ponto, sentido e linha; não posições GPS brutas."""
    if len(crossings)<3:
        return {'status':'insufficient_sample','n':max(0,len(crossings)-1),'mean_minutes':None,'cv':None}
    groups={(x['route_id'],x['direction'],x['stop_id']) for x in crossings}
    if len(groups)!=1:
        raise ValueError('Passagens precisam ter mesma linha, sentido e ponto')
    values=sorted(timestamp(x['observed_at']) for x in crossings)
    gaps=[(b-a).total_seconds()/60 for a,b in zip(values,values[1:])]
    mean=statistics.mean(gaps)
    return {'status':'available','n':len(gaps),'mean_minutes':mean,
            'cv':statistics.pstdev(gaps)/mean if mean>0 else None,'p50_minutes':statistics.median(gaps),
            'algorithm_version':VERSION}
