import { useEffect, useRef } from "react";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { attachArchiveToProtocol, registerPMTiles } from "../pmtiles";
import {
  emptyCollection,
  geometryBounds,
  selectedShapes,
  routeColor,
  findArea,
  areaColor,
} from "../map-data";
import { stopPopup } from "../map-popups";
import { currentVehicles, brDate, number } from "../data";
import type { RuntimeProps } from "./MapRuntime";
/** Ícone de direção criado localmente: sem dependência de glyphs ou requisições externas. */
function addHeadingImage(m: maplibregl.Map) {
  if (m.hasImage("gobus-heading")) return;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.beginPath();
  ctx.moveTo(32, 4);
  ctx.lineTo(52, 48);
  ctx.lineTo(32, 39);
  ctx.lineTo(12, 48);
  ctx.closePath();
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "#164744";
  ctx.lineWidth = 5;
  ctx.lineJoin = "round";
  ctx.stroke();
  ctx.fill();
  m.addImage("gobus-heading", ctx.getImageData(0, 0, 64, 64));
}
export default function MapLibreRuntime(
  props: RuntimeProps & { onUnsupported: () => void },
) {
  const node = useRef<HTMLDivElement>(null),
    map = useRef<maplibregl.Map | null>(null),
    latest = useRef(props);
  latest.current = props;
  const apply = () => {
    const m = map.current;
    if (!m?.getSource("selected-area")) return;
    const p = latest.current;
    for (const name of ["bairros", "setores"])
      if (m.getLayer(name))
        m.setLayoutProperty(
          name,
          "visibility",
          (p.style.theme === "setores" ? "setores" : "bairros") === name ? "visible" : "none",
        );
    if(m.getLayer("bairros"))m.setPaintProperty("bairros","fill-color",[
      "match",["get","BAIRRO"],
      ...p.data.neighborhoods.features.flatMap(f=>[String(f.properties?.BAIRRO),areaColor(f.properties??{},p.style.theme,p.style.neighborhoodMetrics)]),
      "#d6dcdf",
    ] as any);
    if (m.getLayer("paradas")) {
      m.setLayoutProperty(
        "paradas",
        "visibility",
        p.style.showStops === false ? "none" : "visible",
      );
      const filters: any[] = ["all"];
      if(p.style.stopIds)filters.push(["in",["to-string",["get","stop_id"]],["literal",p.style.stopIds]]);
      if(p.style.routeIds.length)filters.push([
              "any",
              ...p.style.routeIds.map((id) => [
                "in",
                "," + id + ",",
                [
                  "concat",
                  ",",
                  ["to-string", ["coalesce", ["get", "route_ids_csv"], ""]],
                  ",",
                ],
              ]),
            ]);
      m.setFilter("paradas",filters.length>1?filters as any:null);
    }
    if (m.getLayer("linhas"))
      m.setFilter("linhas", [
        "in",
        ["get", "route_id"],
        ["literal", p.style.routeIds],
      ]);
    const feature = p.data.neighborhoods.features.find(
      (f) => f.properties?.BAIRRO === p.neighborhood,
    );
    (m.getSource("selected-area") as GeoJSONSource)?.setData(
      feature
        ? { type: "FeatureCollection", features: [feature] }
        : emptyCollection,
    );
    const vehicles = currentVehicles(p.data.vehicles.vehicles).map((v) => ({
      type: "Feature" as const,
      geometry: {
        type: "Point" as const,
        coordinates: [v.longitude, v.latitude],
      },
      properties: {
        id: v.vehicle_id,
        line: v.route_id,
        observed_at: v.observed_at,
        fetched_at: v.fetched_at,
        time_basis: v.time_basis ?? "source_gps",
        signal_status: v.signal_status ?? "ok",
        stale_polls: v.stale_polls ?? 0,
        source_itinerary_id: v.source_itinerary_id || "",
        route_relation: v.route_relation || "unknown",
        bearing: v.bearing ?? 0,
        has_bearing: typeof v.bearing === "number" && Number.isFinite(v.bearing),
      },
    }));
    (m.getSource("vehicles") as GeoJSONSource)?.setData({
      type: "FeatureCollection",
      features: vehicles,
    });
  };
  useEffect(() => {
    if (!node.current) return;
    let disposed = false,
      loaded = false;
    let m: maplibregl.Map;
    try {
      registerPMTiles(maplibregl);
      const url = attachArchiveToProtocol(
        props.data.mapManifest?.file,
        props.data.mapManifest?.sha256,
      );
      m = new maplibregl.Map({
        container: node.current,
        style: {
          version: 8,
          sources: { territory: { type: "vector", url: "pmtiles://" + url } },
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#edf3ee" },
            },
          ],
        },
        center: [-51.18, -29.9],
        zoom: 11,
        minZoom: 8,
        maxZoom: 20,
        attributionControl: { compact: true },
      });
      map.current = m;
    } catch {
      props.onUnsupported();
      return;
    }
    m.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    const timeout = window.setTimeout(() => {
      if (!loaded && !disposed) latest.current.onUnsupported();
    }, 10000);
    m.on("load", () => {
      if (disposed) return;
      loaded = true;
      clearTimeout(timeout);
      const density: any = [
        "/",
        [
          "to-number",
          ["coalesce", ["get", "POPULACAO_2022"], ["get", "pop"]],
          0,
        ],
        [
          "max",
          0.001,
          [
            "to-number",
            ["coalesce", ["get", "AREA_KM2"], ["get", "area_km2"]],
            1,
          ],
        ],
      ];
      for (const name of ["bairros", "setores"])
        m.addLayer({
          id: name,
          type: "fill",
          source: "territory",
          "source-layer": name,
          paint: {
            "fill-color": [
              "step",
              density,
              "#d7ead6",
              3000,
              "#a4d1b4",
              10000,
              "#4b9a86",
              20000,
              "#176557",
            ],
            "fill-opacity": 0.7,
            "fill-outline-color": "#729e90",
          },
        });
      m.addLayer({
        id: "limite",
        type: "line",
        source: "territory",
        "source-layer": "limite",
        paint: {
          "line-color": "#163f43",
          "line-width": 2,
          "line-dasharray": [3, 2],
        },
      });
      if (props.data.mapManifest?.layers.linhas) {
        const palette = props.data.network.routes.flatMap((r) => [
          r.id,
          routeColor(r.id),
        ]);
        m.addLayer({
          id: "linhas",
          type: "line",
          source: "territory",
          "source-layer": "linhas",
          filter: ["in", ["get", "route_id"], ["literal", []]],
          layout: { "line-join": "round", "line-cap": "round" },
          paint: {
            "line-color": [
              "match",
              ["get", "route_id"],
              ...palette,
              "#ae5425",
            ] as any,
            "line-width": 5,
          },
        });
      }
      if (props.data.mapManifest?.layers.paradas)
        m.addLayer({
          id: "paradas",
          type: "circle",
          source: "territory",
          "source-layer": "paradas",
          paint: {
            "circle-radius": 4,
            "circle-color": "#9f6a18",
            "circle-stroke-color": "#fff",
            "circle-stroke-width": 1,
          },
        });
      m.addSource("selected-area", { type: "geojson", data: emptyCollection });
      m.addLayer({
        id: "selected-area",
        type: "line",
        source: "selected-area",
        paint: { "line-color": "#e78c34", "line-width": 3 },
      });
      m.addSource("vehicles", { type: "geojson", data: emptyCollection });
      m.addLayer({
        id: "vehicles",
        type: "circle",
        source: "vehicles",
        paint: {
          "circle-radius": 9,
          "circle-color": [
            "match", ["get", "signal_status"],
            "SC", "#737f84", "SG", "#bb7b25", "#13766a",
          ],
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 2,
        },
      });
      addHeadingImage(m);
      if (m.hasImage("gobus-heading"))
        m.addLayer({
          id: "vehicles-headings",
          type: "symbol",
          source: "vehicles",
          filter: ["all", ["==", ["get", "has_bearing"], true], ["==", ["get", "signal_status"], "ok"]],
          layout: {
            "icon-image": "gobus-heading",
            "icon-size": 0.38,
            "icon-rotate": ["get", "bearing"],
            "icon-rotation-alignment": "map",
            "icon-allow-overlap": true,
          },
        });
      const bounds = geometryBounds(props.data.boundary.features);
      if (bounds) m.fitBounds(bounds, { padding: 25, duration: 0 });
      apply();
      const selectedBounds = geometryBounds(
        selectedShapes(latest.current.data, latest.current.style.routeIds)
          .features,
      );
      if (selectedBounds)
        m.fitBounds(selectedBounds, { padding: 35, maxZoom: 15, duration: 0 });
      latest.current.onState(
        "ready",
        "PMTiles local carregado · MapLibre / WebGL",
      );
    });
    m.on("error", () => {
      if (!loaded && !disposed) latest.current.onUnsupported();
    });
    m.on("click", (event) => {
      const foundStops = m.getLayer("paradas")
        ? m.queryRenderedFeatures(event.point, { layers: ["paradas"] })
        : [];
      if (foundStops.length) {
        const f = latest.current.data.stops.features.find(
          (f) =>
            String(f.properties?.stop_id) ===
            String(foundStops[0].properties.stop_id),
        );
        if (f)
          new maplibregl.Popup()
            .setLngLat(event.lngLat)
            .setDOMContent(stopPopup(f))
            .addTo(m);
        return;
      }
      const vehicles = m.getLayer("vehicles")
        ? m.queryRenderedFeatures(event.point, { layers: ["vehicles"] })
        : [];
      const div = document.createElement("div");
      if (vehicles.length) {
        const p = vehicles[0].properties;
        const signal = p.signal_status === "SC" ? "sem comunicação" : p.signal_status === "SG" ? "sem GPS" : "sinal recebido";
        const age = Math.max(0, Math.floor((Date.now() - Date.parse(p.fetched_at)) / 1000));
        div.textContent = `Veículo ${p.id} · linha de referência ${p.line} · consulta ${brDate(p.fetched_at, true)} (há ${age} s) · ${signal}. ${p.time_basis === "client_fetch" ? "Sem timestamp original do GPS; sentido e itinerário não homologados." : ""}`;
      } else {
        const f = findArea(latest.current.data, latest.current.style.theme, [
          event.lngLat.lng,
          event.lngLat.lat,
        ]);
        if (!f) return;
        div.textContent = String(
          f.properties?.BAIRRO || "Setor " + f.properties?.id,
        );
        const metric=latest.current.style.neighborhoodMetrics?.[String(f.properties?.BAIRRO)];
        if(metric)div.textContent+=' · '+number(metric.stops_per_km2,1)+' paradas/km² · '+number(metric.covered_area_pct,1)+'% da área até 300 m de uma parada publicada. Não comprova atendimento.';
        if (f.properties?.BAIRRO) latest.current.onArea(f.properties.BAIRRO);
      }
      new maplibregl.Popup()
        .setLngLat(event.lngLat)
        .setDOMContent(div)
        .addTo(m);
    });
    const observer = new ResizeObserver(() => m.resize());
    observer.observe(node.current);
    const timer = setInterval(apply, 15000);
    return () => {
      disposed = true;
      clearTimeout(timeout);
      clearInterval(timer);
      observer.disconnect();
      m.remove();
      map.current = null;
    };
  }, [props.data.mapManifest?.file, props.data.mapManifest?.sha256]);
  useEffect(() => {
    apply();
    const m = map.current;
    if (!m) return;
    const selected = selectedShapes(props.data, props.style.routeIds);
    const bounds = geometryBounds(selected.features);
    if (bounds) m.fitBounds(bounds, { padding: 35, maxZoom: 15 });
    else if (props.neighborhood) {
      const f = props.data.neighborhoods.features.filter(
        (f) => f.properties?.BAIRRO === props.neighborhood,
      );
      const b = geometryBounds(f);
      if (b) m.fitBounds(b, { padding: 25, maxZoom: 14 });
    }
  }, [JSON.stringify(props.style), props.neighborhood, props.data.routeShapes]);
  useEffect(() => {
    apply();
  }, [props.data.vehicles]);

  useEffect(() => {
    const m = map.current;
    const f = props.data.stops.features.find(
      (f) => String(f.properties?.stop_id) === props.focusedStopId,
    );
    if (!m || f?.geometry.type !== "Point") return;
    m.flyTo({ center: f.geometry.coordinates as [number, number], zoom: 16 });
    new maplibregl.Popup()
      .setLngLat(f.geometry.coordinates as [number, number])
      .setDOMContent(stopPopup(f))
      .addTo(m);
  }, [props.focusedStopId, props.data.stops]);
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const type = props.command.type;
    if (type === "fit" || type === "route") {
      const features =
        type === "route"
          ? selectedShapes(props.data, props.style.routeIds).features
          : props.data.boundary.features;
      const bounds = geometryBounds(features);
      if (bounds)
        m.fitBounds(bounds, {
          padding: 30,
          maxZoom: type === "route" ? 15 : 14,
        });
    }
    if (type === "locate") {
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
          new maplibregl.Marker({ color: "#a76123" })
            .setLngLat([p.coords.longitude, p.coords.latitude])
            .addTo(m);
          m.flyTo({
            center: [p.coords.longitude, p.coords.latitude],
            zoom: 15,
          });
        },
        () =>
          props.onState("error", "Localização não autorizada ou indisponível."),
        { timeout: 10000 },
      );
    }
  }, [props.command.id]);
  return (
    <div
      ref={node}
      className="map-canvas"
      role="region"
      aria-label="Mapa interativo de Canoas"
    />
  );
}
