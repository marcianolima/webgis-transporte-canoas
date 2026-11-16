import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { ArrowDownToLine, BusFront, CalendarDays, FileArchive, Info, MapPin, Route as RouteIcon } from "lucide-react";
import type { ChangeEvent } from "react";
import type { AppData } from "../types";
import { base, csv, download, number } from "../data";
import { isServiceActive, loadGtfsUpload, serviceFirstTime, serviceLastTime } from "../gtfs";
import type { GtfsFeed } from "../gtfs";

function timeLabel(time:string) {
  if(!time)return "Não informado";
  const hour=Number(time.slice(0,2));
  return time.slice(0,5)+(hour>=24?" (+1 dia)":"");
}
function normalize(value:string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
}
export default function GtfsExplorer({data}:{data:AppData}) {
  const [feed,setFeed]=useState<GtfsFeed|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [query,setQuery]=useState("");
  const [lineCode,setLineCode]=useState("");
  const [variantId,setVariantId]=useState("");
  const [serviceDate,setServiceDate]=useState(()=>new Date().toLocaleDateString("sv-SE",{timeZone:"America/Sao_Paulo"}));
  const mapNode=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    const controller=new AbortController();
    fetch(base+"data/gtfs-canoas.zip",{signal:controller.signal}).then(response=>{
      if(!response.ok)throw Error("Feed GTFS não publicado neste deploy");
      return response.blob();
    }).then(blob=>loadGtfsUpload(new File([blob],"GTFS Canoas publicado.zip",{type:"application/zip"})))
      .then(result=>{if(!controller.signal.aborted){setFeed(result);setLineCode(result.routes[0]?.route_short_name??"");setVariantId(result.routes[0]?.route_id??"");}})
      .catch(()=>{});
    return ()=>controller.abort();
  },[]);
  const lines=useMemo(()=>{
    if(!feed)return [];
    const ids=new Set<string>();
    return feed.routes.filter(r=>{if(ids.has(r.route_short_name))return false;ids.add(r.route_short_name);return true;})
      .sort((a,b)=>a.route_short_name.localeCompare(b.route_short_name,"pt-BR"));
  },[feed]);
  const filteredLines=useMemo(()=>lines.filter(r=>
    normalize(r.route_short_name+" "+r.route_long_name).includes(normalize(query))
  ),[lines,query]);
  const variants=useMemo(()=>feed?.routes.filter(r=>r.route_short_name===lineCode)??[],[feed,lineCode]);
  const chosen=variants.find(v=>v.route_id===variantId)??variants[0];
  const day=useMemo(()=>new Date(serviceDate+"T12:00:00"),[serviceDate]);
  const activeServices=useMemo(()=>new Set(feed?.calendars.filter(c=>isServiceActive(c,day)).map(c=>c.service_id)??[]),[feed,day]);
  const trips=useMemo(()=>feed?.trips.filter(t=>t.route_id===chosen?.route_id&&activeServices.has(t.service_id)).sort((a,b)=>serviceFirstTime(feed,a).localeCompare(serviceFirstTime(feed,b)))??[],[feed,chosen,activeServices]);
  const displayedTrips=useMemo(()=>trips.map(t=>({trip:t,start:feed?serviceFirstTime(feed,t):"",end:feed?serviceLastTime(feed,t):""})),[feed,trips]);
  const representative=trips[0]??feed?.trips.find(t=>t.route_id===chosen?.route_id);
  const path=feed?.shapes.get(representative?.shape_id??"")??[];
  const stopSequence=feed?.timesByTrip.get(representative?.trip_id??"")??[];
  const servedStops=stopSequence.map(t=>({sequence:t.stop_sequence,stop:feed?.stopById.get(t.stop_id)})).filter((s):s is {sequence:number;stop:NonNullable<typeof s.stop>}=>!!s.stop);
  const hourCounts=useMemo(()=>{
    const count=new Map<number,number>();
    for(const t of displayedTrips)if(t.start){const h=Number(t.start.slice(0,2));count.set(h,(count.get(h)??0)+1);}
    return [...count].sort((a,b)=>a[0]-b[0]);
  },[displayedTrips]);
  const maxHour=Math.max(1,...hourCounts.map(v=>v[1]));
  useEffect(()=>{
    if(!feed)return;
    if(!lineCode||!feed.routes.some(r=>r.route_short_name===lineCode)){
      const first=feed.routes[0];setLineCode(first.route_short_name);setVariantId(first.route_id);
    }
  },[feed,lineCode]);
  useEffect(()=>{
    if(!mapNode.current||!feed)return;
    const map=L.map(mapNode.current,{zoomControl:true,attributionControl:false,scrollWheelZoom:false});
    map.setView([-29.91,-51.17],12);
    const outlines=L.geoJSON(data.boundary as import("geojson").GeoJsonObject,{style:{color:"#8597a7",weight:2,fillOpacity:0.03}}).addTo(map);
    if(path.length){
      const layer=L.polyline(path,{color:"#176f85",weight:5,opacity:0.95}).addTo(map);
      for(const item of servedStops){
        L.circleMarker([item.stop.stop_lat,item.stop.stop_lon],{radius:4,color:"#ffffff",weight:1.5,fillColor:"#d97706",fillOpacity:1})
          .bindTooltip(item.sequence+" · "+item.stop.stop_name).addTo(map);
      }
      map.fitBounds(layer.getBounds().pad(0.12));
    }else if(outlines.getBounds().isValid())map.fitBounds(outlines.getBounds());
    const timer=window.setTimeout(()=>map.invalidateSize(),100);
    return ()=>{window.clearTimeout(timer);map.remove();};
  },[feed,chosen?.route_id,representative?.shape_id,representative?.trip_id,data.boundary]);
  async function importFiles(event:ChangeEvent<HTMLInputElement>) {
    const files=Array.from(event.target.files??[]);
    event.target.value="";
    if(!files.length)return;
    setLoading(true);setError("");
    try{
      const result=await loadGtfsUpload(files.length===1&&files[0].name.toLowerCase().endsWith(".zip")?files[0]:files);
      setFeed(result);setLineCode(result.routes[0]?.route_short_name??"");setVariantId(result.routes[0]?.route_id??"");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setLoading(false);}
  }
  const exportTrips=displayedTrips.map(({trip,start,end})=>({
    route_id:trip.route_id,route_short_name:chosen?.route_short_name??"",
    trip_id:trip.trip_id,service_id:trip.service_id,direction_id:trip.direction_id,
    hora_inicial_observada:start,hora_final_observada:end,shape_id:trip.shape_id
  }));
  return <div className="gtfs-page">
    <section className="panel gtfs-heading">
      <div><span className="tag">GTFS STATIC · REFERÊNCIA DOCUMENTAL</span>
        <h2>Explorador GTFS de Canoas</h2>
        <p>Linhas, variantes, trajetos e horários programados. Integrado ao WebGIS sem substituir nem misturar o cadastro TACOM existente.</p>
      </div>
      <label className="gtfs-import">
        <FileArchive size={18}/>
        <span>{loading?"Processando o feed…":"Abrir GTFS ZIP ou arquivos .txt"}</span>
        <input aria-label="Importar GTFS ZIP ou arquivos TXT" type="file" accept=".zip,.txt" multiple disabled={loading} onChange={importFiles}/>
      </label>
    </section>
    {!feed&&<section className="notice warning gtfs-empty">
      <Info size={20}/>
      <div><strong>Selecione o arquivo Dados GTFS.zip para explorar os dados.</strong>
        <p>O arquivo é processado no próprio navegador, sem enviar o conteúdo a serviços externos. Alternativamente, extraia o ZIP e selecione conjuntamente os arquivos .txt. O feed não foi publicado automaticamente a partir do anexo da conversa.</p>
        <p>Auditoria do anexo: 76 códigos de linha, 122 variantes GTFS, 1.582 paradas, 2.860 viagens e 47.990 vértices de trajetos. Vigência declarada: 06/11/2026–06/02/2027.</p>
      </div>
    </section>}
    {error&&<p className="notice warning" role="alert">{error}</p>}
    {feed&&<>
      <div className="gtfs-kpis">
        <div><small>Linhas por código</small><strong>{number(lines.length)}</strong></div>
        <div><small>Variantes / route_id</small><strong>{number(feed.routes.length)}</strong></div>
        <div><small>Paradas geográficas</small><strong>{number(feed.stops.length)}</strong></div>
        <div><small>Viagens programadas</small><strong>{number(feed.trips.length)}</strong></div>
      </div>
      <p className="caption">Origem: {feed.sourceName} · carregamento local {new Date(feed.loadedAt).toLocaleString("pt-BR")}. Programação estática, não comprovação de execução; não se trata de rastreamento GPS.</p>
      <div className="gtfs-layout">
        <section className="panel gtfs-lines">
          <h3><BusFront size={17}/> Linhas cadastradas</h3>
          <input aria-label="Buscar linha GTFS" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Buscar código ou nome"/>
          <p className="caption">{number(filteredLines.length)} de {number(lines.length)} códigos</p>
          <div className="gtfs-line-items">
            {filteredLines.map(r=><button type="button" key={r.route_short_name} className={lineCode===r.route_short_name?"gtfs-active":""}
              onClick={()=>{setLineCode(r.route_short_name);setVariantId(feed.routes.find(v=>v.route_short_name===r.route_short_name)!.route_id);}}>
              <strong>{r.route_short_name}</strong><span>{r.route_long_name}</span>
            </button>)}
          </div>
        </section>
        <div className="gtfs-detail">
          <section className="panel">
            <div className="gtfs-detail-header"><div>
              <h2><RouteIcon size={19}/> {chosen?.route_short_name??"Linha"}</h2>
              <p>{chosen?.route_long_name??"Selecione uma linha"}</p>
            </div><div className="gtfs-mini-kpis"><span>{variants.length} variantes</span><span>{servedStops.length} paradas na viagem de referência</span></div></div>
            <div className="gtfs-controls">
              <label>Itinerário / sentido
                <select aria-label="Variante GTFS" value={chosen?.route_id??""} onChange={e=>setVariantId(e.target.value)}>
                  {variants.map(v=><option key={v.route_id} value={v.route_id}>{v.route_long_name} · ID {v.route_id}</option>)}
                </select>
              </label>
              <label><CalendarDays size={15}/> Data de serviço
                <input aria-label="Data de serviço GTFS" type="date" value={serviceDate} onChange={e=>setServiceDate(e.target.value)}/>
              </label>
            </div>
            <div className="gtfs-map" ref={mapNode} role="img" aria-label="Mapa do itinerário GTFS selecionado com paradas numeradas"/>
            <p className="caption">Linha em azul: geometria do shape_id {representative?.shape_id??"indisponível"}. Pontos em laranja: sequência de paradas de uma viagem de referência. Não é localização do veículo nem garantia de operação.</p>
          </section>
          <section className="panel">
            <div className="section-heading"><div><h2><CalendarDays size={17}/> Programação GTFS</h2>
              <p>{number(trips.length)} viagens na data selecionada · horários de partida efetivamente preenchidos</p></div>
              <button disabled={!trips.length} onClick={()=>download("gtfs-canoas-"+(chosen?.route_short_name??"linha")+".csv",csv(exportTrips),"text/csv")}>
                <ArrowDownToLine size={16}/> Exportar CSV
              </button>
            </div>
            {!activeServices.size&&<p role="status" className="notice warning">A data está fora da vigência declarada ou não há serviço válido para esse dia. Nenhuma viagem foi simulada.</p>}
            {activeServices.size>0&&!trips.length&&<p role="status">Sem viagens cadastradas para este itinerário e data.</p>}
            {hourCounts.length>0&&<div className="gtfs-hour-chart" aria-label="Partidas conhecidas por hora">
              {hourCounts.map(([h,count])=><div key={h} title={h+"h · "+count+" partidas"}><span style={{height:(count/maxHour*100)+"%"}}/><small>{h}h</small></div>)}
            </div>}
            <div className="table-scroll"><table><thead><tr><th>Viagem</th><th>Sentido GTFS</th><th>Primeiro horário preenchido</th><th>Último horário preenchido</th><th>Serviço</th></tr></thead>
              <tbody>{displayedTrips.map(({trip,start,end})=><tr key={trip.trip_id}><td>{trip.trip_id}</td><td>{trip.direction_id==="0"?"0 · ida":trip.direction_id==="1"?"1 · volta":trip.direction_id||"—"}</td><td>{timeLabel(start)}</td><td>{timeLabel(end)}</td><td>{trip.service_id}</td></tr>)}</tbody>
            </table></div>
            <p className="caption">Os horários intermediários não preenchidos no stop_times.txt permanecem ausentes. Intervalos, pontualidade, ETA e realização de viagens não são inferidos a partir do GTFS estático.</p>
          </section>
          <section className="panel">
            <h2><MapPin size={17}/> Paradas em sequência</h2>
            <div className="gtfs-stops-list">{servedStops.map(s=><div key={s.sequence+"-"+s.stop.stop_id}><b>{s.sequence}</b><span>{s.stop.stop_name}<small> ID {s.stop.stop_id}</small></span></div>)}</div>
          </section>
        </div>
      </div>
      <section className="panel">
        <h2>Integrações e cautelas metodológicas</h2>
        <p>A identificação GTFS (route_id, shape_id, stop_id) foi mantida separada dos IDs TACOM e da programação NGS. Coincidência textual do código da linha não confirma equivalência de sentidos ou itinerários.</p>
        <p>Na interface do Observatório de Segurança Viária fornecida como referência, somente 2.049 de 7.664 sinistros tinham pontos cartografados. Uma futura análise de exposição em corredores de ônibus exigirá os registros originais georreferenciados, validação temporal e explicitação dos sinistros sem posição; proximidade espacial não demonstra causalidade.</p>
        <p className="caption">A tarifa 0,00 presente em fare_attributes.txt não deve ser apresentada como tarifa vigente sem validação oficial. O calendário GTFS não contém exceções em calendar_dates.txt neste pacote.</p>
      </section>
    </>}
  </div>;
}
