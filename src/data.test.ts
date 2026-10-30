import {describe,it,expect} from 'vitest';
import {brDate,csv,currentVehicles,filterDepartures,freshness,headways,groupSchedules} from './data';
import type {Departure,Vehicle} from './types';
// Fixtures sintéticas isoladas. Não entram nos dados publicados.
const dep=(minute:number,sequence:number,direction='TEST'):Departure=>({route_id:'SYNTHETIC',date:'2026-01-01',direction,time:'00:00',service_minute:minute,sequence,accessibility_source:null,source_id:'SYNTHETIC',url:'https://example.invalid',fetched_at:'2026-01-01T00:00:00Z',sha256:'SYNTHETIC'});
describe('programação e exportação',()=>{
 it('separa sentidos antes de calcular intervalos',()=>{const rows=[dep(600,0),dep(620,1),dep(610,0,'OTHER'),dep(640,1,'OTHER')];expect(headways(rows)).toEqual([20,30]);expect(groupSchedules(rows)).toHaveLength(2)});
 it('filtra linha data sentido e hora de serviço',()=>{const rows=[dep(1430,0),dep(1450,1)];expect(filterDepartures(rows,'SYNTHETIC','2026-01-01','',1440,2880)).toHaveLength(1);expect(filterDepartures(rows,'OTHER','2026-01-01')).toHaveLength(0)});
 it('escapa aspas, separadores e fórmulas no CSV',()=>{const value=csv([{name:'=SYNTHETIC()',value:'a;"b'}]);expect(value).toContain("'=");expect(value).toContain('a;""b')});
 it('apresenta data no fuso de Brasília',()=>{expect(brDate('2026-01-01T02:00:00Z')).toBe('31/12/2025');expect(brDate('2026-01-01')).toBe('01/01/2026')});
 it('não considera data futura ou inválida recente',()=>{expect(freshness('invalid')).toBe('invalid');expect(freshness('2026-01-02T00:00:00Z',48,Date.parse('2026-01-01T00:00:00Z'))).toBe('invalid')});
 it('retira posições antigas ou futuras',()=>{const now=Date.parse('2026-01-01T00:00:00Z');const vehicle={vehicle_id:'SYNTHETIC',latitude:-29.92,longitude:-51.18} as Vehicle;expect(currentVehicles([{...vehicle,observed_at:'2025-12-31T23:50:00Z'},{...vehicle,observed_at:'2026-01-01T00:00:00Z'},{...vehicle,observed_at:'2026-01-01T01:00:00Z'}],now)).toHaveLength(1)});
});
