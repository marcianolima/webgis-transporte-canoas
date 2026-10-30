"""Contratos públicos observados no bundle do portal vinculado pela Sogal."""
from urllib.parse import urlencode
from .parsing import rows, ordered_service_minutes

BASE = 'https://ngsservicos.com/aplicativos/NgPortais/sogal/scripts/'
PORTAL = 'https://ngsservicos.com/sogal/horarios/'
SOURCE = 'sogal-ngs'


class NGS:
    def __init__(self, fetcher):
        self.http = fetcher

    def _get(self, script, params=None, required=(), ttl=86400):
        url = BASE + script + ('?' + urlencode(params) if params else '')
        record = self.http.get(url, ttl=ttl)
        return rows(record['body'], required), {k: record[k] for k in ('url', 'fetched_at', 'sha256')}

    def dates(self):
        return self._get('getDataLiberada.php', required=('DATA', 'DIA'), ttl=3600)

    def routes(self, date):
        return self._get('getLinhas.php', {'DATA': date}, ('LINHA', 'NOME_COMPLETO'))

    def schedule(self, route, date):
        data, provenance = self._get('getEspHorario.php', {'LINHA': route, 'DATA': date}, ('LINHA',))
        departures = []
        for item in data:
            if str(item['LINHA']) != route:
                raise ValueError('Horário pertence a outra linha')
            for key, direction_key in [('HRS_BC', 'SENTIDO'), ('HRS_CB', 'SENTIDO_2')]:
                values = item.get(key) or []
                if not isinstance(values, list):
                    raise ValueError('Horários fora do contrato')
                times = ordered_service_minutes([x['HR_IV'] for x in values])
                for n, (value, minute) in enumerate(zip(values, times)):
                    departures.append({'route_id': route, 'date': date, 'direction': item.get(direction_key) or key,
                        'time': value['HR_IV'], 'service_minute': minute, 'sequence': n,
                        'accessibility_source': value.get('APD'), 'source_id': SOURCE, **provenance})
        return departures, provenance

    def itinerary(self, route):
        return self._get('getItinerario.php', {'LINHA': route}, ('ORDEM', 'NOME_LOG'), ttl=604800)
