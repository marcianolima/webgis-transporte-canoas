/**
 * Leitor GTFS independente da coleta TACOM/GoBus.
 * Aceita ZIP local (deflate-raw) ou os .txt descompactados no navegador.
 * Não estima localização de veículos, ETAs nem horários intermediários ausentes.
 */
export type Row = Record<string, string>;
export type Point = [number, number];
export interface GtfsRoute {
  route_id: string; route_short_name: string; route_long_name: string;
  network_id: string; route_type: string;
}
export interface GtfsTrip {
  trip_id: string; route_id: string; service_id: string;
  shape_id: string; direction_id: string;
}
export interface GtfsStop {stop_id:string; stop_name:string; stop_lat:number; stop_lon:number}
export interface GtfsStopTime {
  trip_id:string; stop_id:string; stop_sequence:number;
  arrival_time:string; departure_time:string;
}
export interface GtfsCalendar {
  service_id:string; start_date:string; end_date:string;
  monday:string;tuesday:string;wednesday:string;thursday:string;
  friday:string;saturday:string;sunday:string;
}
export interface GtfsFeed {
  routes:GtfsRoute[]; trips:GtfsTrip[]; stops:GtfsStop[];
  stopById:Map<string,GtfsStop>;
  timesByTrip:Map<string,GtfsStopTime[]>;
  shapes:Map<string,Point[]>; calendars:GtfsCalendar[];
  counts:{shapePoints:number; stopTimes:number};
  sourceName:string; loadedAt:string;
}
const required=["routes.txt","trips.txt","stops.txt","stop_times.txt","shapes.txt","calendar.txt"];
const allowed=new Set([...required,"agency.txt","fare_rules.txt","fare_attributes.txt"]);
const decoder=new TextDecoder("utf-8");
function safeCount(n:number,max:number,label:string) {
  if (!Number.isSafeInteger(n)||n<0||n>max)throw Error("GTFS fora do limite: "+label);
}
export function parseCsv(text:string):Row[] {
  const src=text.replace(/^\uFEFF/,"");
  const records:string[][]=[];let row:string[]=[],value="",quoted=false;
  for(let i=0;i<src.length;i++){
    const c=src[i];
    if(c==='"'){
      if(quoted&&src[i+1]==='"'){value+='"';i++;}
      else quoted=!quoted;
    }else if(c===","&&!quoted){row.push(value);value="";}
    else if((c==="\n"||c==="\r")&&!quoted){
      if(c==="\r"&&src[i+1]==="\n")i++;
      row.push(value);value="";
      if(row.some(v=>v.trim()))records.push(row);
      row=[];
    }else value+=c;
  }
  if(quoted)throw Error("CSV GTFS: aspas não fechadas");
  row.push(value);
  if(row.some(v=>v.trim()))records.push(row);
  const head=records.shift()??[];
  if(!head.length||head.some(v=>!v.trim()))throw Error("Cabeçalho CSV GTFS inválido");
  return records.map((values)=>Object.fromEntries(head.map((field,i)=>[field,values[i]??""])));
}
export function parseGtfs(files:Record<string,string>,sourceName="GTFS local"):GtfsFeed {
  for(const name of required)if(!files[name])throw Error("Arquivo obrigatório ausente: "+name);
  const read=(name:string,keys:string[])=>{
    const rows=parseCsv(files[name]);
    if(!rows.length||keys.some(k=>!(k in rows[0])))throw Error("GTFS inválido em "+name);
    return rows;
  };
  const routes=read("routes.txt",["route_id","route_short_name","route_long_name"]) as unknown as GtfsRoute[];
  const trips=read("trips.txt",["trip_id","route_id","service_id","shape_id"]) as unknown as GtfsTrip[];
  const stopRows=read("stops.txt",["stop_id","stop_name","stop_lat","stop_lon"]);
  const timeRows=read("stop_times.txt",["trip_id","stop_id","stop_sequence"]);
  const shapeRows=read("shapes.txt",["shape_id","shape_pt_lat","shape_pt_lon","shape_pt_sequence"]);
  const calendars=read("calendar.txt",["service_id","start_date","end_date"]) as unknown as GtfsCalendar[];
  const stops=stopRows.map(s=>({...s,stop_lat:Number(s.stop_lat),stop_lon:Number(s.stop_lon)})) as unknown as GtfsStop[];
  if(stops.some(s=>!Number.isFinite(s.stop_lat)||!Number.isFinite(s.stop_lon)||Math.abs(s.stop_lat)>90||Math.abs(s.stop_lon)>180))throw Error("Parada com coordenada inválida");
  const stopById=new Map(stops.map(s=>[s.stop_id,s]));
  const routeIds=new Set(routes.map(r=>r.route_id));
  const tripIds=new Set(trips.map(t=>t.trip_id));
  const services=new Set(calendars.map(c=>c.service_id));
  if(trips.some(t=>!routeIds.has(t.route_id)||!services.has(t.service_id)))throw Error("GTFS com viagem sem linha ou serviço");
  const timesByTrip=new Map<string,GtfsStopTime[]>();
  for(const r of timeRows){
    if(!tripIds.has(r.trip_id)||!stopById.has(r.stop_id))throw Error("stop_times referencia trip_id ou stop_id ausente");
    const s={...r,stop_sequence:Number(r.stop_sequence)} as GtfsStopTime;
    if(!Number.isInteger(s.stop_sequence)||s.stop_sequence<0)throw Error("stop_sequence inválida");
    if(!timesByTrip.has(s.trip_id))timesByTrip.set(s.trip_id,[]);
    timesByTrip.get(s.trip_id)!.push(s);
  }
  for(const v of timesByTrip.values())v.sort((a,b)=>a.stop_sequence-b.stop_sequence);
  const shapeSequences=new Map<string,{seq:number;point:Point}[]>();
  for(const r of shapeRows){
    const lat=Number(r.shape_pt_lat),lon=Number(r.shape_pt_lon),seq=Number(r.shape_pt_sequence);
    if(!Number.isFinite(lat)||!Number.isFinite(lon)||!Number.isFinite(seq))throw Error("shapes inválido");
    if(!shapeSequences.has(r.shape_id))shapeSequences.set(r.shape_id,[]);
    shapeSequences.get(r.shape_id)!.push({seq,point:[lat,lon]});
  }
  const shapes=new Map([...shapeSequences].map(([id,values])=>[id,values.sort((a,b)=>a.seq-b.seq).map(v=>v.point)]));
  if(trips.some(t=>t.shape_id&&!shapes.has(t.shape_id)))throw Error("GTFS com shape_id inexistente");
  return {routes,trips,stops,stopById,timesByTrip,shapes,calendars,
    counts:{shapePoints:shapeRows.length,stopTimes:timeRows.length},
    sourceName,loadedAt:new Date().toISOString()};
}
export function serviceFirstTime(feed:GtfsFeed,trip:GtfsTrip):string {
  return feed.timesByTrip.get(trip.trip_id)?.find(t=>t.departure_time||t.arrival_time)?.departure_time||
    feed.timesByTrip.get(trip.trip_id)?.find(t=>t.departure_time||t.arrival_time)?.arrival_time||"";
}
export function serviceLastTime(feed:GtfsFeed,trip:GtfsTrip):string {
  return [...(feed.timesByTrip.get(trip.trip_id)??[])].reverse().find(t=>t.arrival_time||t.departure_time)?.arrival_time||
    [...(feed.timesByTrip.get(trip.trip_id)??[])].reverse().find(t=>t.arrival_time||t.departure_time)?.departure_time||"";
}
export function isServiceActive(service:GtfsCalendar,day:Date) {
  const date=day.getFullYear().toString()+String(day.getMonth()+1).padStart(2,"0")+String(day.getDate()).padStart(2,"0");
  const field=(["sunday","monday","tuesday","wednesday","thursday","friday","saturday"] as const)[day.getDay()];
  return date>=service.start_date&&date<=service.end_date&&service[field]==="1";
}
async function textFromZip(file:File):Promise<Record<string,string>> {
  safeCount(file.size,35_000_000,"arquivo ZIP");
  const buffer=await file.arrayBuffer(), view=new DataView(buffer);
  let end=-1;
  for(let i=buffer.byteLength-22;i>=Math.max(0,buffer.byteLength-65557);i--)
    if(view.getUint32(i,true)===0x06054b50){end=i;break;}
  if(end<0)throw Error("ZIP sem diretório central válido");
  const entries=view.getUint16(end+10,true),dir=view.getUint32(end+16,true);
  safeCount(entries,300,"quantidade de arquivos");
  let offset=dir,total=0;
  const files:Record<string,string>={};
  for(let i=0;i<entries;i++){
    if(offset+46>buffer.byteLength||view.getUint32(offset,true)!==0x02014b50)throw Error("Diretório ZIP corrompido");
    const method=view.getUint16(offset+10,true),compressed=view.getUint32(offset+20,true);
    const uncompressed=view.getUint32(offset+24,true),nameSize=view.getUint16(offset+28,true);
    const extra=view.getUint16(offset+30,true),comment=view.getUint16(offset+32,true);
    const local=view.getUint32(offset+42,true);
    const name=decoder.decode(new Uint8Array(buffer,offset+46,nameSize));
    offset+=46+nameSize+extra+comment;
    const basename=name.split("/").pop()!.toLowerCase();
    if(!allowed.has(basename))continue;
    if(files[basename]!==undefined)throw Error("Arquivo GTFS repetido: "+basename);
    safeCount(uncompressed,25_000_000,basename);
    total+=uncompressed;safeCount(total,50_000_000,"conteúdo ZIP");
    if(local+30>buffer.byteLength||view.getUint32(local,true)!==0x04034b50)throw Error("Cabeçalho ZIP inválido");
    const start=local+30+view.getUint16(local+26,true)+view.getUint16(local+28,true);
    if(start+compressed>buffer.byteLength)throw Error("Arquivo ZIP truncado");
    const bytes=buffer.slice(start,start+compressed);
    let content:ArrayBuffer;
    if(method===0)content=bytes;
    else if(method===8){
      if(typeof DecompressionStream==="undefined")throw Error("Navegador sem descompressão ZIP; extraia os arquivos .txt");
      try {
        const ds=new DecompressionStream("deflate-raw" as CompressionFormat);
        content=await new Response(new Blob([bytes]).stream().pipeThrough(ds)).arrayBuffer();
      }catch{throw Error("Não foi possível abrir ZIP neste navegador. Extraia os .txt e importe-os diretamente.");}
    }else throw Error("ZIP usa método de compactação incompatível");
    if(content.byteLength!==uncompressed)throw Error("Tamanho do arquivo ZIP divergente: "+basename);
    files[basename]=decoder.decode(content);
  }
  return files;
}
export async function loadGtfsUpload(upload:File|File[]):Promise<GtfsFeed> {
  const files:Record<string,string>={};
  if(!Array.isArray(upload))return parseGtfs(await textFromZip(upload),upload.name);
  for(const file of upload){
    const name=file.name.toLowerCase();
    if(allowed.has(name)){safeCount(file.size,25_000_000,name);files[name]=await file.text();}
  }
  return parseGtfs(files,"Arquivos GTFS locais");
}
