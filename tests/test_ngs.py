import hashlib
from pathlib import Path
import pytest
from transporte.ngs import NGS
from transporte.parsing import rows
FIX=Path(__file__).parent/'fixtures'
class Local:
    def get(self,url,ttl=None):
        name='ngs-schedule-real-2026-10-30.json' if 'getEspHorario' in url else 'ngs-itinerary-real.json'
        b=(FIX/name).read_bytes()
        return {'url':url,'body':b.decode('utf-8-sig'),'sha256':hashlib.sha256(b).hexdigest(),'fetched_at':'2026-10-30T22:00:00+00:00'}

def test_homologated_schedule_contract():
    departures,provenance=NGS(Local()).schedule('05000','2026-10-30')
    assert departures and {d['route_id'] for d in departures}=={'05000'}
    assert len({d['direction'] for d in departures})==2
    assert any(d['service_minute']==1440 for d in departures)
    assert len(provenance['sha256'])==64

def test_homologated_itinerary_contract():
    values,_=NGS(Local()).itinerary('05000')
    assert len(values)==63 and all(v['CIDADE']=='Canoas' for v in values)

def test_wrong_route_rejected():
    with pytest.raises(ValueError):NGS(Local()).schedule('OTHER','2026-10-30')
