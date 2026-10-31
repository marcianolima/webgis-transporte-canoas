"""Teste de até cinco paradas distintas de uma linha de Canoas.

Sonda de leitura limitada (máximo 9 GET), sem publicação de coordenadas,
veículos, placas ou payloads de previsões. Nenhum polling automático.
"""
import argparse
import json
import time
import urllib.request
from transporte.gobus import lines,line_cities,stops,predictions,itinerary
from scripts.gobus_capture_geography import get,NoRedirect

def normalized(code):
    value=str(code or '').strip()
    return value.lstrip('0') or '0'

def investigate(opener,pause=time.sleep,route_code='05006'):
    raw,_=get(opener,'cidades_linhas',{'cidade':'MPA'})
    city=[c['city_id'] for c in line_cities(raw.decode('utf-8-sig'))
          if c['name'].upper().strip()=='CANOAS']
    if city!=['4']:raise ValueError('codcid=4 não confirmado')
    pause(2)
    raw,_=get(opener,'linhas')
    source=lines(raw.decode('utf-8-sig'))
    municipal=[r for r in source if str(r.get('codcid'))=='4' and r.get('praca')=='MPA']
    matches=[r for r in municipal if normalized(r['sgl'])==normalized(route_code)]
    if len(matches)!=1:raise ValueError('Linha escolhida ambígua')
    siu_line=str(matches[0]['cod'])
    municipal_codes={normalized(x['sgl']) for x in municipal}
    pause(2)
    raw,_=get(opener,'paradas_geograficas',{'linha':siu_line,'cidade':'MPA'})
    geo=stops(raw.decode('utf-8-sig'))
    valid=[r for r in geo if 'longitude' in r and -51.4<=r['longitude']<=-50.95
           and -30.12<=r['latitude']<=-29.65 and r['stop_id'].isdecimal()]
    indexes=sorted(set([0,len(valid)//4,len(valid)//2,(3*len(valid))//4,len(valid)-1])) if valid else []
    result={'municipality_code':'4304606','verified_city_code':'4',
            'sample_line':route_code,'source_stops':len(geo),
            'valid_stops':len(valid),'sampled_stops':0,'predictions_seen':0,
            'matching_municipal_predictions':0,'itinerary_vertices':None,
            'itinerary_geo_within_area':None,'gps_collected':False,
            'status':'no_active_itinerary_in_sample'}
    selected=None
    for idx in indexes:
        pause(3)
        raw,_=get(opener,'previsoes',{'parada':valid[idx]['stop_id'],
                                     'acessivel':'false','cidade':'MPA'})
        predictions_here=predictions(raw.decode('utf-8-sig'))
        result['sampled_stops']+=1
        result['predictions_seen']+=len(predictions_here)
        approved=[p for p in predictions_here
                  if normalized(p.get('sgLin')) in municipal_codes
                  and str(p.get('codItinerario') or '').isdecimal()]
        result['matching_municipal_predictions']+=len(approved)
        if approved:
            selected=approved[0]
            break
    if not selected:return result
    pause(3)
    itinerary_id=str(selected['codItinerario'])
    raw,_=get(opener,'itinerario',{'itinerario':itinerary_id,'cidade':'MPA'})
    feature=itinerary(raw.decode('utf-8-sig'),itinerary_id)
    coordinates=feature['geometry']['coordinates']
    inside=all(-51.4<=lon<=-50.95 and -30.12<=lat<=-29.65 for lon,lat in coordinates)
    result['itinerary_vertices']=len(coordinates)
    result['itinerary_geo_within_area']=inside
    result['sample_itinerary_route_code']=str(selected.get('sgLin'))
    result['status']='geometry_endpoint_confirmed_for_municipal_line' if inside else 'needs_geographic_review'
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autorizado',action='store_true')
    p.add_argument('--aceito-http',action='store_true')
    args=p.parse_args()
    if not args.autorizado or not args.aceito_http:
        p.error('Exige autorização e ciência de HTTP legado')
    value=investigate(urllib.request.build_opener(NoRedirect))
    print(json.dumps(value,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
