import { useEffect, useRef } from "react";
import L from "leaflet";
import type { Feature } from "geojson";
import "leaflet/dist/leaflet.css";
import { currentVehicles, number, brDate } from "../data";
import {
  areaColor,
  findArea,
  selectedShapes,
  routeColor,
  selectedStops,
} from "../map-data";
import { LocalVectorLayer, mapArchive, type TileStyle } from "../pmtiles";
import { stopPopup } from "../map-popups";
import type { AppData } from "../types";
export type MapState = "loading" | "ready" | "fallback" | "error";
export interface RuntimeProps {
  data: AppData;
  style: TileStyle;
  neighborhood: string;
  focusedStopId?: string;
  command: { type: string; id: number };
  onState: (state: MapState, message: string) => void;
  onArea: (name: string) => void;
}
export default function MapRuntime(props: RuntimeProps) {
  const container = useRef<HTMLDivElement>(null),
    map = useRef<L.Map | null>(null),
    tiles = useRef<LocalVectorLayer | null>(null),
    selection = useRef<L.GeoJSON | null>(null),
    stopLayer = useRef<L.GeoJSON | null>(null),
    highlight = useRef<L.GeoJSON | null>(null),
    legacy = useRef<L.LayerGroup | null>(null),
    state = useRef(props);
  state.current = props;
  useEffect(() => {
    if (!container.current) return;
    let removed = false,
      mode: "loading" | "pmtiles" | "fallback" = "loading";
    const m = L.map(container.current, {
      zoomControl: false,
      scrollWheelZoom: true,
      minZoom: 8,
      maxZoom: 20,
      preferCanvas: false,
    });
    map.current = m;
    L.control.zoom({ position: "topright" }).addTo(m);
    const all = L.geoJSON(props.data.boundary);
    if (all.getBounds().isValid())
      m.fitBounds(all.getBounds(), { padding: [22, 22] });
    else m.setView([-29.9, -51.18], 11);
    selection.current = L.geoJSON(undefined, {
      style: (f) => ({
        color: routeColor(String(f?.properties?.route_id)),
        weight: 5,
        opacity: 0.95,
      }),
      onEachFeature: (f, l) => {
        const node = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = "Linha " + f.properties?.route_id;
        const p = document.createElement("p");
        p.textContent =
          String(f.properties?.direction || "Sentido não informado") +
          " · " +
          String(
            f.properties?.source_name ||
              f.properties?.source_url ||
              "Fonte identificada no cadastro",
          ) +
          " · conferir vigência";
        node.append(title, p);
        if(f.properties?.source_route_name){const name=document.createElement('p');name.textContent='Nome na API: '+String(f.properties.source_route_name);node.append(name)}
        const detail = document.createElement("p");
        detail.textContent =
          "Itinerário " +
          String(
            f.properties?.itinerary_id ||
              f.properties?.shape_id ||
              "não informado",
          ) +
          " · consulta " +
          brDate(f.properties?.fetched_at, true) +
          (f.properties?.territorial_quality === "border_review"
            ? " · trecho na borda da base de bairros: revisar delimitação."
            : "");
        node.append(detail);
        l.bindPopup(node);
      },
    }).addTo(m);
    highlight.current = L.geoJSON(undefined, {
      style: { color: "#e78c34", weight: 3, fillOpacity: 0 },
    }).addTo(m);
    stopLayer.current = L.geoJSON(undefined, {
      pointToLayer: (_feature, latlng) =>
        L.circleMarker(latlng, {
          radius: 4.5,
          color: "#fff",
          weight: 1.3,
          fillColor: "#9f6a18",
          fillOpacity: 0.95,
        }),
      onEachFeature: (f, l) => l.bindPopup(stopPopup(f)),
    }).addTo(m);
    legacy.current = L.layerGroup();
    const paintLegacy = () => {
      legacy.current?.clearLayers();
      const active =
        state.current.style.theme === "setores"
          ? props.data.sectors
          : props.data.neighborhoods;
      legacy.current?.addLayer(
        L.geoJSON(active, {
          style: (f) => ({
            color: state.current.style.theme === "setores" ? "#fff" : "#3a6860",
            weight: 0.7,
            fillColor: areaColor(f?.properties??{},state.current.style.theme,state.current.style.neighborhoodMetrics),
            fillOpacity: 0.6,
          }),
        }),
      );
      legacy.current?.addLayer(
        L.geoJSON(props.data.boundary, {
          style: { color: "#163f43", weight: 2, fill: false, dashArray: "5 4" },
        }),
      );
      legacy.current?.addTo(m);
      selection.current?.bringToFront();
      highlight.current?.bringToFront();
    };
    const fallback = () => {
      if (removed || mode === "fallback") return;
      mode = "fallback";
      if (tiles.current) m.removeLayer(tiles.current);
      paintLegacy();
      state.current.onState(
        "fallback",
        "PMTiles indisponível neste acesso. As geometrias GeoJSON locais mantêm o mapa funcionando.",
      );
    };
    const archive = mapArchive(
      props.data.mapManifest?.file,
      props.data.mapManifest?.sha256,
    );
    const layer = new LocalVectorLayer(
      archive,
      () => state.current.style,
      (count) => {
        if (removed || mode === "fallback" || count === 0) return;
        mode = "pmtiles";
        state.current.onState("ready", "Base local PMTiles carregada");
      },
      fallback,
    );
    tiles.current = layer;
    layer.addTo(m);
    const timeout = window.setTimeout(() => {
      if (mode === "loading") fallback();
    }, 8000);
    const repaint = () => {
      if (mode === "fallback") paintLegacy();
    };
    m.on("map-style-change", repaint);
    m.on("click", (event) => {
      const current = state.current;
      const f = findArea(current.data, current.style.theme, [
        event.latlng.lng,
        event.latlng.lat,
      ]);
      if (!f) return;
      const p = f.properties || {};
      const node = document.createElement("div"),
        title = document.createElement("strong"),
        text = document.createElement("p");
      title.textContent = String(p.BAIRRO || "Setor " + p.id);
      text.textContent =
        number(p.POPULACAO_2022 ?? p.pop) +
        " habitantes · referência Censo 2022";
      node.append(title, text);
      const metric=current.style.neighborhoodMetrics?.[String(p.BAIRRO)];
      if(metric){const detail=document.createElement('p');detail.textContent=number(metric.stops_per_km2,1)+' paradas/km² · '+number(metric.covered_area_pct,1)+'% da área até 300 m de uma parada publicada. Referência estática; não comprova atendimento.';node.append(detail)}
      L.popup().setLatLng(event.latlng).setContent(node).openOn(m);
      if (p.BAIRRO) current.onArea(p.BAIRRO);
    });
    const markers = new Map<string, L.CircleMarker>();
    const update = () => {
      const values = currentVehicles(state.current.data.vehicles.vehicles);
      const keys = new Set(values.map((v) => v.source_id + ":" + v.vehicle_id));
      for (const [id, marker] of markers)
        if (!keys.has(id)) {
          m.removeLayer(marker);
          markers.delete(id);
        }
      for (const v of values) {
        const id = v.source_id + ":" + v.vehicle_id;
        const existing = markers.get(id);
        if (existing) existing.setLatLng([v.latitude, v.longitude]);
        else {
          const node = document.createElement("div");
          node.textContent = `Veículo ${v.vehicle_id} · linha ${v.route_id} · ${brDate(v.observed_at, true)}`;
          markers.set(
            id,
            L.circleMarker([v.latitude, v.longitude], {
              radius: 7,
              color: "#fff",
              weight: 2,
              fillColor: routeColor(v.route_id),
              fillOpacity: 1,
            })
              .bindPopup(node)
              .addTo(m),
          );
        }
      }
    };
    update();
    const timer = setInterval(update, 15000);
    const resize = () => m.invalidateSize({ pan: false });
    const observer =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    observer?.observe(container.current);
    window.addEventListener("resize", resize);
    requestAnimationFrame(resize);
    return () => {
      removed = true;
      clearTimeout(timeout);
      clearInterval(timer);
      observer?.disconnect();
      window.removeEventListener("resize", resize);
      m.remove();
      map.current = null;
      tiles.current = null;
      selection.current = null;
      highlight.current = null;
      stopLayer.current = null;
      legacy.current = null;
    };
  }, [
    props.data.neighborhoods,
    props.data.sectors,
    props.data.boundary,
    props.data.stops,
    props.data.mapManifest?.file,
    props.data.mapManifest?.sha256,
  ]);
  const styleKey = JSON.stringify(props.style);
  useEffect(() => {
    tiles.current?.redraw();
    map.current?.fire("map-style-change");
    const layer = selection.current;
    if (layer) {
      layer.clearLayers();
      layer.addData(selectedShapes(props.data, props.style.routeIds));
      layer.bringToFront();
      stopLayer.current?.clearLayers();
      if (props.style.showStops !== false)
        stopLayer.current?.addData(
          selectedStops(props.data, props.style.routeIds),
        );
      stopLayer.current?.bringToFront();
      if (layer.getBounds().isValid())
        map.current?.fitBounds(layer.getBounds(), {
          padding: [35, 35],
          maxZoom: 15,
        });
      else if (
        props.style.routeIds.length &&
        stopLayer.current?.getBounds().isValid()
      )
        map.current?.fitBounds(stopLayer.current.getBounds(), {
          padding: [35, 35],
          maxZoom: 15,
        });
    }
  }, [styleKey, props.data.routeShapes, props.data.stops]);
  useEffect(() => {
    if (!props.focusedStopId) return;
    stopLayer.current?.eachLayer((layer) => {
      const f = (layer as L.Layer & { feature?: Feature }).feature;
      if (String(f?.properties?.stop_id) === props.focusedStopId) {
        const marker = layer as L.CircleMarker;
        map.current?.setView(marker.getLatLng(), 16);
        marker.openPopup();
      }
    });
  }, [props.focusedStopId, props.data.stops, styleKey]);
  useEffect(() => {
    highlight.current?.clearLayers();
    if (props.neighborhood) {
      const f = props.data.neighborhoods.features.find(
        (f) => f.properties?.BAIRRO === props.neighborhood,
      );
      if (f) {
        highlight.current?.addData(f);
        const bounds = highlight.current?.getBounds();
        if (bounds?.isValid())
          map.current?.fitBounds(bounds, { padding: [25, 25], maxZoom: 14 });
      }
    }
  }, [props.neighborhood, props.data.neighborhoods]);
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    if (props.command.type === "fit") {
      const b = L.geoJSON(props.data.boundary).getBounds();
      if (b.isValid()) m.fitBounds(b, { padding: [22, 22] });
    }
    if (props.command.type === "route") {
      const selectedBounds = selection.current?.getBounds();
      const b = selectedBounds?.isValid()
        ? selectedBounds
        : stopLayer.current?.getBounds();
      if (b?.isValid()) m.fitBounds(b, { padding: [35, 35], maxZoom: 15 });
    }
    if (props.command.type === "locate") {
      if (!navigator.geolocation) {
        props.onState(
          "error",
          "Geolocalização não disponível neste navegador.",
        );
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (p) => {
          if (map.current !== m) return;
          const node = document.createElement("div");
          node.textContent =
            "Sua localização · utilizada apenas neste navegador";
          L.circleMarker([p.coords.latitude, p.coords.longitude], {
            radius: 7,
            color: "#a76123",
          })
            .bindPopup(node)
            .addTo(m);
          m.setView([p.coords.latitude, p.coords.longitude], 15);
        },
        () =>
          props.onState("error", "Localização não autorizada ou indisponível."),
        { timeout: 10000 },
      );
    }
  }, [props.command.id]);
  return (
    <div
      className="map-canvas"
      ref={container}
      role="region"
      aria-label="Mapa interativo de Canoas"
    />
  );
}
