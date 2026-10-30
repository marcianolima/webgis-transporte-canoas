"""python -m transporte.collect --days 5. Coleta estática; nunca coleta GPS."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .http import Fetcher, utcnow
from .ngs import NGS, SOURCE, PORTAL

ROOT = Path(__file__).resolve().parents[2]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    temporary.replace(path)


def collect(days=5, root=ROOT, interval=0.75):
    public = root / 'public/data'
    private = root / 'var'
    http = Fetcher(private / 'cache', interval=interval)
    ngs = NGS(http)
    started = utcnow()
    db = sqlite3.connect(private / 'static-history.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS snapshot(kind TEXT, natural_key TEXT, hash TEXT, observed_at TEXT, payload TEXT, PRIMARY KEY(kind,natural_key,hash))')
    db.execute('CREATE TABLE IF NOT EXISTS run(started_at TEXT PRIMARY KEY, ended_at TEXT, status TEXT, errors TEXT)')
    db.execute('INSERT INTO run VALUES (?,?,?,?)', (started, None, 'running', '[]'))
    db.commit()
    routes, departures, errors, date_records = {}, [], [], []
    try:
        dates, date_provenance = ngs.dates()
        if not dates:
            raise ValueError('Fonte sem datas: preservar última publicação')
        dates = sorted(dates, key=lambda x: x['DATA'])[:days]
        for date in dates:
            day = date['DATA']
            route_rows, provenance = ngs.routes(day)
            if not route_rows:
                errors.append({'date': day, 'resource': 'routes', 'error': 'Lista vazia; data não homologada'})
                continue
            day_errors = []
            def collect_route(pair):
                i, item = pair
                code = str(item['LINHA'])
                route = routes.setdefault(code, {'id': code, 'code': code.lstrip('0') or '0',
                    'name': item['NOME_COMPLETO'].strip(), 'source_id': SOURCE,
                    'scope': 'municipal', 'dates': [], 'itinerary': [], 'itinerary_status': 'pending', **provenance})
                route['dates'].append(day)
                try:
                    values, _ = ngs.schedule(code, day)
                    departures.extend(values)
                except Exception as exc:
                    error = {'route_id': code, 'date': day, 'resource': 'schedule', 'error': str(exc)}
                    errors.append(error)
                    day_errors.append(code)
                if route['itinerary_status'] == 'pending':
                    try:
                        itinerary, ip = ngs.itinerary(code)
                        route['itinerary'] = [{'sequence': int(x['ORDEM']), 'street': x['NOME_LOG'], 'street_type': x.get('TP_LOG'), 'city': x.get('CIDADE')} for x in itinerary]
                        route['itinerary_provenance'] = ip
                        route['itinerary_status'] = 'available' if itinerary else 'empty'
                    except Exception as exc:
                        errors.append({'route_id': code, 'resource': 'itinerary', 'error': str(exc)})
                if i % 10 == 0:
                    print(json.dumps({'event': 'progress', 'date': day, 'route': i + 1, 'total': len(route_rows)}, ensure_ascii=False), flush=True)
            # Duas conexões no máximo, limitador GLOBAL compartilhado e sem consultas GPS.
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(collect_route, enumerate(route_rows)))
            date_records.append({'date': day, 'routes': len(route_rows), 'failed_routes': day_errors, 'complete': not day_errors})
        if not routes or not departures:
            raise ValueError('Nenhum horário validado; preservar última publicação')
        # Deduplicação preserva sequência: partidas distintas no mesmo minuto podem existir.
        unique = {(d['route_id'], d['date'], d['direction'], d['sequence']): d for d in departures}
        departures = list(unique.values())
        output = {'schema_version': 1, 'generated_at': utcnow(), 'source_id': SOURCE, 'source_url': PORTAL,
            'source_dates': date_records, 'routes': sorted(routes.values(), key=lambda x: x['id']),
            'departures': departures, 'errors': errors, 'status': 'partial' if errors else 'available',
            'limitations': ['Saídas programadas; não comprovam viagens realizadas.', 'Itinerário textual sem sentido ou variante homologados.', 'APD preservado sem interpretação não homologada.', 'Cadastro por data; não equivale ao total de linhas ativas.']}
        for kind, values, key in [('route', output['routes'], lambda v: v['id']), ('schedule', departures, lambda v: '|'.join(str(v[k]) for k in ('route_id','date','direction','sequence')))]:
            for value in values:
                stable = {k: v for k, v in value.items() if k not in ('fetched_at','sha256','url','itinerary_provenance')}
                payload = json.dumps(stable, ensure_ascii=False, sort_keys=True)
                digest = hashlib.sha256(payload.encode()).hexdigest()
                db.execute('INSERT OR IGNORE INTO snapshot VALUES (?,?,?,?,?)', (kind, key(value), digest, utcnow(), payload))
        dump(public / 'network.json', output)
        dump(root / 'research/collection-evidence.json', {'started_at': started, 'ended_at': utcnow(), 'requests': http.records, 'errors': errors})
        db.execute('INSERT OR REPLACE INTO run VALUES (?,?,?,?)', (started, utcnow(), output['status'], json.dumps(errors)))
        db.commit()
        print(json.dumps({'event': 'done', 'routes': len(routes), 'departures': len(departures), 'errors': len(errors)}, ensure_ascii=False), flush=True)
        return output
    except Exception as exc:
        db.execute('INSERT OR REPLACE INTO run VALUES (?,?,?,?)', (started, utcnow(), 'failed', json.dumps([str(exc)])))
        db.commit()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=5, choices=range(1, 6))
    parser.add_argument('--interval', type=float, default=0.75)
    args = parser.parse_args()
    if args.interval < 0.5:
        parser.error('Intervalo mínimo 0,5 s')
    collect(args.days, interval=args.interval)
