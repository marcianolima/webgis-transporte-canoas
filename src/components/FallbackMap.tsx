import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Layers, LocateFixed, Maximize } from "lucide-react";
import { currentVehicles, number } from "../data";
import type { AppData } from "../types";
export default function FallbackMap({
  data,
  territorial = false,
}: {
  data: AppData;
  territorial?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null),
    map = useRef<L.Map | null>(null),
    neighborhoodLayer = useRef<L.GeoJSON | null>(null),
    sectorLayer = useRef<L.GeoJSON | null>(null),
    tiles = useRef<L.TileLayer | null>(null);
  const vehicleState = useRef(data.vehicles);
  vehicleState.current = data.vehicles;
  const [layer, setLayer] = useState("bairros"),
    [streets, setStreets] = useState(false),
    [message, setMessage] = useState("");
  useEffect(() => {
    if (!ref.current) return;
    const m = L.map(ref.current, {
      zoomControl: false,
      scrollWheelZoom: false,
      attributionControl: true,
    });
    map.current = m;
    L.control.zoom({ position: "topright" }).addTo(m);
    const t = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors",
    });
    tiles.current = t;
    t.on("tileerror", () => {
      setStreets(false);
      setMessage(
        "Fundo viário indisponível. As camadas locais continuam disponíveis.",
      );
    });
    const color = (density: number) =>
      density > 20000
        ? "#176557"
        : density > 10000
          ? "#4b9a86"
          : density > 3000
            ? "#a4d1b4"
            : "#d7ead6";
    const popup = (properties: Record<string, any>, sector = false) => {
      const node = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = sector
        ? "Setor " + properties.id
        : properties.BAIRRO ||
          properties.name ||
          properties.vehicle_id ||
          "Ponto de parada";
      const p = document.createElement("p");
      p.textContent = sector
        ? number(properties.pop) + " habitantes · Censo 2022"
        : properties.BAIRRO
          ? number(properties.POPULACAO_2022) + " habitantes · Censo 2022"
          : properties.observed_at
            ? "Linha " + properties.route_id + " · " + properties.observed_at
            : "OpenStreetMap · atendimento municipal não confirmado";
      node.append(title, p);
      return node;
    };
    const neighborhoods = L.geoJSON(data.neighborhoods, {
      style: (f) => ({
        color: "#1b5a5d",
        weight: 1,
        fillColor: color(
          (f?.properties?.POPULACAO_2022 || 0) /
            Math.max(0.01, f?.properties?.AREA_KM2 || 1),
        ),
        fillOpacity: territorial ? 0.6 : 0.35,
      }),
      onEachFeature: (f, l) => l.bindPopup(popup(f.properties)),
    }).addTo(m);
    neighborhoodLayer.current = neighborhoods;
    const sectors = L.geoJSON(data.sectors, {
      style: (f) => ({
        color: "#f4f7f4",
        weight: 0.4,
        fillColor: color(
          (f?.properties?.pop || 0) /
            Math.max(0.001, f?.properties?.area_km2 || 1),
        ),
        fillOpacity: 0.7,
      }),
      onEachFeature: (f, l) => l.bindPopup(popup(f.properties, true)),
    });
    sectorLayer.current = sectors;
    L.geoJSON(data.boundary, {
      style: { color: "#123e42", weight: 2, fill: false, dashArray: "5 4" },
    }).addTo(m);
    L.geoJSON(data.stops, {
      pointToLayer: (_, p) =>
        L.circleMarker(p, {
          radius: 5,
          color: "#fff",
          weight: 1,
          fillColor: "#9f6a18",
          fillOpacity: 1,
        }),
      onEachFeature: (f, l) => l.bindPopup(popup(f.properties)),
    }).addTo(m);
    const markers = new Map<string, L.CircleMarker>();
    const update = () => {
      const valid = currentVehicles(vehicleState.current.vehicles);
      const ids = new Set(valid.map((p) => p.source_id + ":" + p.vehicle_id));
      for (const [id, marker] of markers)
        if (!ids.has(id)) {
          m.removeLayer(marker);
          markers.delete(id);
        }
      for (const p of valid) {
        const id = p.source_id + ":" + p.vehicle_id;
        const existing = markers.get(id);
        if (existing) existing.setLatLng([p.latitude, p.longitude]);
        else
          markers.set(
            id,
            L.circleMarker([p.latitude, p.longitude], {
              radius: 7,
              color: "#fff",
              weight: 2,
              fillColor: "#168563",
              fillOpacity: 1,
            })
              .bindPopup(popup(p))
              .addTo(m),
          );
      }
    };
    update();
    const timer = setInterval(update, 15000);
    if (neighborhoods.getBounds().isValid())
      m.fitBounds(neighborhoods.getBounds(), { padding: [20, 20] });
    else m.setView([-29.9, -51.18], 11);
    const observer = new ResizeObserver(() => m.invalidateSize());
    observer.observe(ref.current);
    return () => {
      clearInterval(timer);
      observer.disconnect();
      m.remove();
      map.current = null;
    };
  }, [
    data.neighborhoods,
    data.sectors,
    data.stops,
    data.boundary,
    territorial,
  ]);
  useEffect(() => {
    const m = map.current,
      n = neighborhoodLayer.current,
      s = sectorLayer.current;
    if (!m || !n || !s) return;
    if (layer === "setores") {
      m.removeLayer(n);
      s.addTo(m);
    } else {
      m.removeLayer(s);
      n.addTo(m);
    }
  }, [layer]);
  useEffect(() => {
    const m = map.current,
      t = tiles.current;
    if (!m || !t) return;
    if (streets) t.addTo(m);
    else m.removeLayer(t);
  }, [streets]);
  const locate = () =>
    navigator.geolocation
      ? navigator.geolocation.getCurrentPosition(
          (p) => {
            map.current?.setView([p.coords.latitude, p.coords.longitude], 15);
            L.circleMarker([p.coords.latitude, p.coords.longitude], {
              radius: 7,
              color: "#ad642a",
            }).addTo(map.current!);
            setMessage("Sua localização é usada apenas neste navegador.");
          },
          () => setMessage("Localização não autorizada ou indisponível."),
          { timeout: 10000 },
        )
      : setMessage("Geolocalização não disponível.");
  return (
    <div className="map-wrap">
      <div
        ref={ref}
        className="map-canvas"
        role="region"
        aria-label="Mapa interativo de Canoas"
      />
      <div className="map-tools">
        <label>
          <Layers size={15} />
          <select
            aria-label="Camada temática"
            value={layer}
            onChange={(e) => setLayer(e.target.value)}
          >
            <option value="bairros">Bairros oficiais</option>
            <option value="setores">Setores · Censo 2022</option>
          </select>
        </label>
        <button aria-pressed={streets} onClick={() => setStreets(!streets)}>
          Ruas
        </button>
        <button onClick={locate} aria-label="Localizar minha posição">
          <LocateFixed size={17} />
        </button>
        <button
          onClick={() => {
            const b = neighborhoodLayer.current?.getBounds();
            if (b) map.current?.fitBounds(b);
          }}
          aria-label="Enquadrar Canoas"
        >
          <Maximize size={17} />
        </button>
      </div>
      <div className="map-legend">
        <strong>Canoas, RS</strong>
        <span>
          {layer === "setores" ? "Setores do Censo 2022" : "Bairros oficiais"} ·
          habitantes/km²
        </span>
        <span className="density-scale">
          0 <i /> ≥ 20 mil
        </span>
        <span>
          Contorno tracejado: união dos bairros, sem homologação como limite
          municipal
        </span>
      </div>
      {message && (
        <p className="map-message" role="status">
          {message}
        </p>
      )}
    </div>
  );
}
