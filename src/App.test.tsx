import React from 'react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import App from './App';
import * as source from './data';
import type {AppData} from './types';
vi.mock('./components/TransportMap',()=>({default:()=> <div>Mapa local disponível</div>}));
vi.mock('./components/Chart',()=>({default:()=> <div>Gráfico com dados programados</div>}));
const geo={type:'FeatureCollection',features:[]} as AppData['neighborhoods'];
const now=new Date().toISOString();
const route={id:'TEST',code:'TEST',name:'SYNTHETIC · fixture isolada',dates:['2026-01-01'],source_id:'sogal-ngs',itinerary:[],itinerary_status:'empty',url:'https://example.invalid',fetched_at:now,sha256:'0'.repeat(64)};
const fixture:AppData={network:{schema_version:1,generated_at:now,source_id:'sogal-ngs',source_url:'https://example.invalid',source_dates:[{date:'2026-01-01',routes:1,complete:true,failed_routes:[]}],routes:[route],departures:[{...route,route_id:'TEST',date:'2026-01-01',direction:'TEST SENTIDO',time:'06:00',service_minute:360,sequence:0,accessibility_source:null}],errors:[],status:'available',limitations:[]},catalogue:{generated_at:now,integrations:[],methodologies:[]},territory:{generated_at:now,neighborhoods:[],stops_status:'unavailable',stops_source:null,sectors:0,limitations:[]},neighborhoods:geo,sectors:geo,stops:geo,boundary:geo,vehicles:{status:'unavailable',generated_at:null,vehicles:[],message:'Fixture sem GPS'}};
afterEach(()=>{cleanup();vi.restoreAllMocks();location.hash='';localStorage.clear()});
describe('fluxos da interface',()=>{
 it('mostra programação e indisponibilidade sem inventar GPS',async()=>{vi.spyOn(source,'loadData').mockResolvedValue(fixture);render(<App/>);await screen.findByText('Saídas programadas');expect(screen.getByText('GPS não homologado')).toBeTruthy();expect(screen.getByRole('heading',{name:'Painel geral'})).toBeTruthy()});
 it('consulta linha e sentido com horário real da fixture',async()=>{vi.spyOn(source,'loadData').mockResolvedValue(fixture);render(<App/>);await screen.findByText('Saídas programadas');location.hash='linhas';window.dispatchEvent(new HashChangeEvent('hashchange'));await screen.findByText('06:00');expect(screen.getByText('TEST SENTIDO')).toBeTruthy();fireEvent.change(screen.getByLabelText('Buscar linha'),{target:{value:'inexistente'}});expect(screen.queryByRole('button',{name:/fixture isolada/})).toBeNull()});
 it('mantém identificação de página e tema ao navegar',async()=>{vi.spyOn(source,'loadData').mockResolvedValue(fixture);render(<App/>);await screen.findByText('Saídas programadas');fireEvent.click(screen.getByLabelText('Usar tema escuro'));expect(document.documentElement.dataset.theme).toBe('dark');location.hash='relatorios';window.dispatchEvent(new HashChangeEvent('hashchange'));await screen.findByLabelText('Linha do relatório');expect(screen.getAllByRole('link',{name:'Relatórios'}).every(a=>a.getAttribute('aria-current')==='page')).toBe(true)});
 it('apresenta falha de carregamento e permite tentar novamente',async()=>{vi.spyOn(source,'loadData').mockRejectedValue(Error('SYNTHETIC erro de rede'));render(<App/>);await screen.findByText('Dados temporariamente indisponíveis');expect(screen.getByRole('button',{name:'Tentar novamente'})).toBeTruthy()});
});
