import {Suspense,lazy,useEffect,useRef,useState} from 'react';
import maplibregl,{type GeoJSONSource} from 'maplibre-gl';
import type {FeatureCollection} from 'geojson';
import 'maplibre-gl/dist/maplibre-gl.css';
import {Layers,LocateFixed,Maximize,MapPin} from 'lucide-react';
import {currentVehicles,number} from '../data';
import type {AppData} from '../types';
const FallbackMap=lazy(()=>import('./FallbackMap'));
const empty:FeatureCollection={type:'FeatureCollection',features:[]};
export default function TransportMap({data,territorial=false,selectedNeighborhood='',onNeighborhood}:{data:AppData;territorial?:boolean;selectedNeighborhood?:string;onNeighborhood?:(name:string)=>void}){
 const container=useRef<HTMLDivElement>(null),map=useRef<maplibregl.Map|null>(null);
 const [fallback,setFallback]=useState(false);
 const [layer,setLayer]=useState('bairros'),[base,setBase]=useState(false),[message,setMessage]=useState(''),[selected,setSelected]=useState('');
 const vehicleState=useRef(data.vehicles);vehicleState.current=data.vehicles;
 const selection=useRef(selectedNeighborhood);selection.current=selectedNeighborhood;
 const callback=useRef(onNeighborhood);callback.current=onNeighborhood;
 useEffect(()=>{
  if(!container.current)return;
  let m:maplibregl.Map;
  try{m=new maplibregl.Map({container:container.current,center:[-51.18,-29.90],zoom:11,attributionControl:false,style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},layers:[{id:'background',type:'background',paint:{'background-color':'#e6eeeb'}},{id:'osm',type:'raster',source:'osm',layout:{visibility:'none'},paint:{'raster-opacity':0.65}}]}})}catch{container.current.replaceChildren();setFallback(true);return}
  map.current=m;m.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right');m.addControl(new maplibregl.AttributionControl({compact:true}),'bottom-left');
  m.on('load',()=>{
   m.addSource('bairros',{type:'geojson',data:data.neighborhoods});m.addSource('setores',{type:'geojson',data:data.sectors});m.addSource('paradas',{type:'geojson',data:data.stops});m.addSource('limite',{type:'geojson',data:data.boundary});m.addSource('veiculos',{type:'geojson',data:empty});
   m.addLayer({id:'bairros-fill',type:'fill',source:'bairros',paint:{'fill-color':['interpolate',['linear'],['/', ['coalesce',['get','POPULACAO_2022'],0],['max',0.01,['coalesce',['get','AREA_KM2'],1]]],0,'#d7ead6',3000,'#a4d1b4',10000,'#4b9a86',20000,'#176557'],'fill-opacity':territorial?0.65:0.22}});
   m.addLayer({id:'setores-fill',type:'fill',source:'setores',layout:{visibility:'none'},paint:{'fill-color':['interpolate',['linear'],['/', ['coalesce',['get','pop'],0],['max',0.001,['coalesce',['get','area_km2'],1]]],0,'#e2edcd',5000,'#b1d5a5',15000,'#579d84',30000,'#164f4f'],'fill-opacity':0.7,'fill-outline-color':'#f4f7f444'}});
   m.addLayer({id:'bairros-line',type:'line',source:'bairros',paint:{'line-color':'#1b5a5d','line-width':1,'line-opacity':0.7}});
   m.addLayer({id:'limite-line',type:'line',source:'limite',paint:{'line-color':'#123e42','line-width':2,'line-dasharray':[3,2]}});
   m.addLayer({id:'selection',type:'line',source:'bairros',filter:['==','BAIRRO',selection.current],paint:{'line-color':'#e78c34','line-width':3}});
   m.addLayer({id:'paradas-dot',type:'circle',source:'paradas',paint:{'circle-radius':5,'circle-color':'#9f6a18','circle-stroke-color':'#fff','circle-stroke-width':1.5}});
   m.addLayer({id:'veiculos-dot',type:'circle',source:'veiculos',paint:{'circle-radius':7,'circle-color':'#168563','circle-stroke-color':'#fff','circle-stroke-width':2}});
   const coords=data.boundary.features.flatMap(f=>JSON.stringify(f.geometry).match(/-?\d+\.\d+/g)?.map(Number)||[]);if(coords.length>3){const bounds=new maplibregl.LngLatBounds();for(let i=0;i<coords.length-1;i+=2)if(coords[i]>=-180&&coords[i]<=180&&coords[i+1]>=-90&&coords[i+1]<=90)bounds.extend([coords[i],coords[i+1]]);if(!bounds.isEmpty())m.fitBounds(bounds,{padding:30,duration:0})}
   const popup=(event:maplibregl.MapLayerMouseEvent,kind:string)=>{const p=event.features?.[0]?.properties;if(!p)return;const node=document.createElement('div');node.className='map-popup';const title=document.createElement('strong');title.textContent=String(p.BAIRRO||p.name||p.vehicle_id||p.id||'Ponto de parada');const content=document.createElement('p');content.textContent=kind==='bairro'?`${number(p.POPULACAO_2022)} habitantes · Censo 2022`:kind==='setor'?`Setor ${p.id} · ${number(p.pop)} habitantes · Censo 2022`:kind==='veiculo'?`Linha ${p.route_id} · posição observada ${p.observed_at}`:'OpenStreetMap · cadastro colaborativo; atendimento municipal não confirmado';node.append(title,content);new maplibregl.Popup({closeButton:true,maxWidth:'280px'}).setLngLat(event.lngLat).setDOMContent(node).addTo(m);if(kind==='bairro'){setSelected(p.BAIRRO);callback.current?.(p.BAIRRO)}};
   m.on('click','bairros-fill',e=>{if(m.getLayoutProperty('setores-fill','visibility')!=='visible')popup(e,'bairro')});m.on('click','setores-fill',e=>popup(e,'setor'));m.on('click','paradas-dot',e=>popup(e,'parada'));m.on('click','veiculos-dot',e=>popup(e,'veiculo'));
   for(const id of ['bairros-fill','paradas-dot','veiculos-dot']){m.on('mouseenter',id,()=>m.getCanvas().style.cursor='pointer');m.on('mouseleave',id,()=>m.getCanvas().style.cursor='')}
   const update=()=>{const source=m.getSource('veiculos') as GeoJSONSource;if(source)source.setData({type:'FeatureCollection',features:currentVehicles(vehicleState.current.vehicles).map(v=>({type:'Feature',geometry:{type:'Point',coordinates:[v.longitude,v.latitude]},properties:{...v}}))})};update();const timer=setInterval(update,15_000);m.once('remove',()=>clearInterval(timer));
  });let tileError=false;m.on('error',e=>{if(e.error.message.includes('tile')&&!tileError){tileError=true;setMessage('Mapa de fundo indisponível. Camadas locais continuam disponíveis.')}});
  return ()=>{m.remove();map.current=null};
 },[data.neighborhoods,data.sectors,data.stops,data.boundary,territorial]);
 useEffect(()=>{const m=map.current;if(m?.getLayer('bairros-fill')){m.setLayoutProperty('setores-fill','visibility',layer==='setores'?'visible':'none');m.setLayoutProperty('bairros-fill','visibility',layer==='setores'?'none':'visible')}},[layer]);
 useEffect(()=>{const m=map.current;if(m?.getLayer('osm'))m.setLayoutProperty('osm','visibility',base?'visible':'none')},[base]);
 useEffect(()=>{const m=map.current;if(m?.getLayer('selection'))m.setFilter('selection',['==','BAIRRO',selectedNeighborhood])},[selectedNeighborhood]);
 const locate=()=>{if(!navigator.geolocation){setMessage('Geolocalização não disponível neste navegador.');return}navigator.geolocation.getCurrentPosition(p=>{map.current?.flyTo({center:[p.coords.longitude,p.coords.latitude],zoom:15});setMessage('Sua localização é usada apenas neste navegador.');new maplibregl.Marker({color:'#ad642a'}).setLngLat([p.coords.longitude,p.coords.latitude]).addTo(map.current!)},()=>setMessage('Localização não autorizada ou indisponível.'),{enableHighAccuracy:false,timeout:10000})};
 if(fallback)return <Suspense fallback={<div className="loading-map">Carregando mapa compatível…</div>}><FallbackMap data={data} territorial={territorial}/></Suspense>;
 return <div className="map-wrap"><div className="map-canvas" ref={container} aria-label="Mapa interativo de Canoas" role="region"/><div className="map-tools"><label><Layers size={15}/><select aria-label="Camada temática" value={layer} onChange={e=>setLayer(e.target.value)}><option value="bairros">Bairros oficiais</option><option value="setores">Setores · Censo 2022</option></select></label><button onClick={()=>setBase(!base)} aria-pressed={base}>Ruas</button><button onClick={locate} aria-label="Localizar minha posição"><LocateFixed size={17}/></button><button onClick={()=>map.current?.fitBounds([[-51.3,-30],[-51.09,-29.8]],{padding:24})} aria-label="Enquadrar Canoas"><Maximize size={17}/></button></div><div className="map-legend"><strong><MapPin size={14}/> Canoas, RS</strong><span><i className="swatch"/> {layer==='setores'?'Densidade populacional por setor':'Bairros oficiais · habitantes/km²'}</span><span className="density-scale">Menor <i/> Maior</span><span>Contorno tracejado: união dos bairros, sem homologação como limite municipal</span>{data.stops.features.length>0&&<span>● Paradas OSM · atendimento não confirmado</span>}{selected&&<span>Selecionado: {selected}</span>}</div>{message&&<p className="map-message" role="status">{message}</p>}</div>
}
