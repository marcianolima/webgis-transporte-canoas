"""Prova limitada do percurso de UMA linha de Canoas.

Somente leitura, até cinco consultas GET (cidade, linhas, paradas, previsões,
itinerário), nenhuma repetição. Não divulga veículo, parada ou GPS bruto.
"""
import argparse
import json
import time
import urllib.request
from transporte.gobus import lines, line_cities, stops, predictions, itinerary
from scripts.gobus_capture_geography import get, NoRedirect

def sample(opener, pause=time.sleep, route_code='05006'):
    if not route_code.isdecimal():
        raise ValueError('Código precisa ser numérico')
    city_raw,_=get(opener,'cidades_linhas',{'cidade':'MPA'})
    cities=[x['city_id'] for x in line_cities(city_raw.decode('utf-8-sig'))
            if x['name'].upper().strip()=='CANOAS']
    if cities!=['4']:
        raise ValueError('Código CANOAS/4 não verificado')
    pause(2)
    source_raw,_=get(opener,'linhas')
    filtered=[r for r in lines(source_raw.decode('utf-8-sig'))
              if str(r.get('codcid'))=='4' and r.get('praca')=='MPA'
              and str(r.get('sgl','')).lstrip('0')==(route_code.lstrip('0') or '0')]
    result={'municipality_code':'4304606','city_code':'4','source_city_group':'MPA',
            'selected_route_code':route_code,'matching_source_line_count':len(filtered),
            'stop_count':None,'stops_with_coordinates':None,'prevision_count':None,
            'route_geometry_vertices':None,'geometry_within_operational_envelope':None,
            'status':'partial','gps_collected':False,'vehicles_published':False}
    if len(filtered)!=1:
        result['reason']='linha com código ambíguo ou ausente'
        return result
    line_id=str(filtered[0]['cod'])
    pause(2)
    raw,_=get(opener,'paradas_geograficas',{'linha':line_id,'cidade':'MPA'})
    geo_stops=stops(raw.decode('utf-8-sig'))
    within=lambda lon,lat: -51.4<=float(lon)<=-50.95 and -30.12<=float(lat)<=-29.65
    local=[s for s in geo_stops if 'longitude' in s and within(s['longitude'],s['latitude'])]
    result['stop_count']=len(geo_stops)
    result['stops_with_coordinates']=len(local)
    if not local:
        result['reason']='paradas geográficas ausentes ou fora do envelope de Canoas'
        return result
    # Apenas uma parada, sem varredura; ausência de previsão é estado legítimo.
    stop_id=local[0]['stop_id']
    if not stop_id.isdecimal():
        result['reason']='parada sem ID numérico'
        return result
    pause(2)
    raw,_=get(opener,'previsoes',{'parada':stop_id,'acessivel':'false','cidade':'MPA'})
    preds=predictions(raw.decode('utf-8-sig'))
    result['prevision_count']=len(preds)
    active=[p for p in preds if str(p.get('sgLin','')).lstrip('0')==(route_code.lstrip('0') or '0')
            and str(p.get('codItinerario','')).isdigit()]
    if not active:
        result['reason']='nenhuma previsão vigente com ID do itinerário desta linha'
        return result
    itinerary_id=str(active[0]['codItinerario'])
    pause(2)
    raw,_=get(opener,'itinerario',{'itinerario':itinerary_id,'cidade':'MPA'})
    geom=itinerary(raw.decode('utf-8-sig'),itinerary_id)
    coordinates=geom['geometry']['coordinates']
    result['route_geometry_vertices']=len(coordinates)
    result['geometry_within_operational_envelope']=all(within(*xy) for xy in coordinates)
    result['status']='sample_geography_confirmed' if result['geometry_within_operational_envelope'] else 'needs_review'
    result['reason']='Amostra efêmera; não é forma/vigência aprovada para publicação'
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autorizado',action='store_true')
    p.add_argument('--aceito-http',action='store_true')
    p.add_argument('--route-code',default='05006')
    args=p.parse_args()
    if not args.autorizado or not args.aceito_http:
        p.error('Confirme autorização e risco de HTTP legado')
    print(json.dumps(sample(urllib.request.build_opener(NoRedirect),route_code=args.route_code),
                     ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
