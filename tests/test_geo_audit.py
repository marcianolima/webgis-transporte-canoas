from datetime import datetime,timezone,timedelta
import pytest
from transporte.geo import valid_coordinate,PROJECT,UNPROJECT
from transporte.audit import normalize_position,trajectory_events,headway_stats

# Identificadores SYNTHETIC exclusivos desta fixture.
def position(seconds=0,**kw):
    p={'source_id':'SYNTHETIC','vehicle_id':'SYNTHETIC-1','route_id':'TEST',
       'observed_at':(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=seconds)).isoformat(),
       'longitude':-51.18,'latitude':-29.92,'scope':'municipal','municipality_code':'4304606'}
    return p|kw

@pytest.mark.parametrize('lon,lat,expected',[(-51.18,-29.92,True),(None,-29.92,False),(0,0,False),(-43,-19,False),(float('nan'),-29,False),(True,-29,False)])
def test_coordinate_validation(lon,lat,expected):assert valid_coordinate(lon,lat)==expected

def test_projection_roundtrip():
    x,y=PROJECT(-51.18,-29.92);assert 470000<x<500000 and 6600000<y<6800000
    lon,lat=UNPROJECT(x,y);assert lon==pytest.approx(-51.18,abs=1e-7) and lat==pytest.approx(-29.92,abs=1e-7)

def test_position_normalization():
    p=normalize_position(position());assert p['observed_at'].endswith('+00:00')

@pytest.mark.parametrize('changes',[{'municipality_code':'4314902'},{'scope':'metropolitan'},{'observed_at':'2026-01-01T00:00:00'},{'speed_kmh':200},{'bearing':float('inf')},{'vehicle_id':None},{'latitude':0}])
def test_reject_invalid_positions(changes):
    with pytest.raises(ValueError):normalize_position(position(**changes))

def test_future_positions():
    with pytest.raises(ValueError):normalize_position(position(60),now=datetime(2026,1,1,tzinfo=timezone.utc))

def test_jump_not_infraction():
    events=trajectory_events([position(),position(10,longitude=-51.10)])
    assert events[0]['kind']=='gps_jump' and events[0]['classification']=='inconclusive' and not events[0]['is_infraction']

def test_no_cross_vehicle_comparison():
    assert not trajectory_events([position(),position(10,longitude=-51.10,vehicle_id='OTHER')])

def test_sampling_gap_not_cancelled_trip():
    events=trajectory_events([position(),position(900)])
    assert [e['kind'] for e in events]==['sampling_gap']

def test_stationary_needs_continuity():
    events=trajectory_events([position(x) for x in range(0,721,120)])
    assert any(e['kind']=='prolonged_stationary' for e in events)
    assert not any(e['kind']=='prolonged_stationary' for e in trajectory_events([position(0),position(900)]))

def test_possible_deviation():
    events=trajectory_events([position(),position(60)],authorized_shape=[[-51.19,-29.91],[-51.19,-29.93]])
    assert events[0]['kind']=='possible_deviation' and events[0]['classification']=='probable'

def test_headway():
    samples=[{'observed_at':position(x)['observed_at'],'route_id':'TEST','direction':'TEST','stop_id':'TEST'} for x in [0,600,1200]]
    value=headway_stats(samples);assert value['mean_minutes']==10 and value['cv']==0 and value['n']==2
    assert headway_stats(samples[:2])['mean_minutes'] is None
    samples[-1]['direction']='OTHER'
    with pytest.raises(ValueError):headway_stats(samples)

def test_conflicting_timestamp_preserves_evidence():
    events=trajectory_events([position(),position(longitude=-51.181)])
    assert events[0]['kind']=='conflicting_position'
