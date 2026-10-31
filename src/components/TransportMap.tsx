import {
  Component,
  Suspense,
  lazy,
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  Layers,
  LocateFixed,
  Maximize,
  Navigation,
  RefreshCw,
  Search,
  MapPin,
} from "lucide-react";
import type { AppData } from "../types";
import { routeColor, selectedShapes, selectedStops } from "../map-data";
import type { MapState } from "./MapRuntime";
const MapRuntime = lazy(() => import("./MapRuntime"));
const MapLibreRuntime = lazy(() => import("./MapLibreRuntime"));
class MapBoundary extends Component<
  { children: ReactNode; retry: () => void },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <div className="map-fatal" role="alert">
        <p>O mapa não pôde iniciar neste navegador.</p>
        <button onClick={this.props.retry}>
          <RefreshCw size={16} />
          Reiniciar no modo compatível
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}
export default function TransportMap({
  data,
  territorial = false,
  selectedRouteIds,
  compact = false,
  selectedNeighborhood = "",
  onNeighborhood,
  focusedStopId,
}: {
  data: AppData;
  territorial?: boolean;
  selectedRouteIds?: string[];
  compact?: boolean;
  selectedNeighborhood?: string;
  focusedStopId?: string;
  onNeighborhood?: (name: string) => void;
}) {
  const [engine, setEngine] = useState("compatible"),
    [theme, setTheme] = useState("bairros"),
    [localIds, setLocalIds] = useState<string[]>([]),
    [query, setQuery] = useState(""),
    [neighborhood, setNeighborhood] = useState(selectedNeighborhood),
    [revision, setRevision] = useState(0),
    [status, setStatus] = useState<MapState>("loading"),
    [message, setMessage] = useState("Carregando mapa local…"),
    [command, setCommand] = useState({ type: "", id: 0 });
  const [showStops, setShowStops] = useState(true);
  const ids = selectedRouteIds ?? localIds;
  const key = ids.join("|");
  const selected = useMemo(
    () => selectedShapes(data, ids),
    [data.routeShapes, key],
  );
  const visibleStops = useMemo(()=>selectedStops(data,ids).features.length,[data.stops,key]);
  const allowedStopIds = useMemo(()=>data.stops.features.map(f=>String(f.properties?.stop_id)),[data.stops]);
  const stateChanged = useCallback((value: MapState, text: string) => {
    setStatus(value);
    setMessage(text);
  }, []);
  const retry = () => {
    setEngine("compatible");
    setRevision((v) => v + 1);
    setStatus("loading");
    setMessage("Reiniciando mapa local…");
  };
  const areaChanged = useCallback(
    (name: string) => {
      setNeighborhood(name);
      onNeighborhood?.(name);
    },
    [onNeighborhood],
  );
  const run = (type: string) => setCommand((c) => ({ type, id: c.id + 1 }));
  const available =
    data.mapManifest?.route_geometry_count ??
    new Set(data.routeShapes?.features.map((f) => f.properties?.route_id)).size;
  const missing = ids.filter(
    (id) =>
      !data.routeShapes?.features.some(
        (f) => String(f.properties?.route_id) === id,
      ),
  );
  const visible = data.network.routes.filter((r) =>
    (r.code + " " + r.name)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .includes(
        query
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase(),
      ),
  );
  const runtimeProps = {
    data,
    style: { theme, routeIds: ids, territorial, showStops, stopIds:allowedStopIds,
      neighborhoodMetrics:Object.fromEntries(data.territory.neighborhoods.map(n=>[n.name,{stops_per_km2:n.stops_per_km2,covered_area_pct:n.covered_area_pct}])) },
    neighborhood,
    focusedStopId,
    command,
    onState: stateChanged,
    onArea: areaChanged,
  };
  return (
    <section
      className={"transport-map " + (compact ? "compact-map" : "")}
      aria-label="Consulta cartográfica do transporte"
    >
      <div className="map-access-controls">
        <label>
          <Layers size={16} />
          <select
            aria-label="Camada temática"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
          >
            <option value="bairros">Bairros oficiais</option>
            <option value="setores">Setores · Censo 2022</option>
            <option value="densidade-paradas" disabled={!data.stops.features.length}>Paradas por km² · bairros</option>
            <option value="cobertura-paradas" disabled={!data.stops.features.length}>Área até 300 m de paradas · bairros</option>
          </select>
        </label>
        <label>
          <span className="sr-only">Bairro do mapa</span>
          <select
            aria-label="Bairro do mapa"
            value={neighborhood}
            onChange={(e) => setNeighborhood(e.target.value)}
          >
            <option value="">Todos os bairros</option>
            {data.territory.neighborhoods.map((n) => (
              <option key={n.name}>{n.name}</option>
            ))}
          </select>
        </label>
        <label className="engine-select">
          <span>Modo</span>
          <select
            aria-label="Modo do mapa"
            value={engine}
            onChange={(e) => {
              setEngine(e.target.value);
              setStatus("loading");
              setMessage("Carregando mapa…");
            }}
          >
            <option value="compatible">Compatível</option>
            <option value="webgl">MapLibre / WebGL</option>
          </select>
        </label>
      </div>
      <div className="map-layer-status">
        <label>
          <input
            type="checkbox"
            checked={showStops}
            onChange={(e) => setShowStops(e.target.checked)}
          />{" "}
          Mostrar paradas de referência ({visibleStops})
        </label>
        <span>{available} linhas com percurso · dados parciais da API</span>
      </div>
      {ids.length>0&&<p className="caption map-filter-note">Filtro ativo: o mapa mostra paradas das linhas selecionadas. Para ver o cadastro completo publicado, limpe a seleção de linhas.</p>}
      <div
        className={
          "transport-map-layout " +
          (selectedRouteIds || compact ? "no-route-panel" : "")
        }
      >
        <div className="map-wrap map-pmtiles">
          <MapBoundary key={engine + revision} retry={retry}>
            <Suspense
              fallback={
                <div className="map-fatal">Carregando motor cartográfico…</div>
              }
            >
              {engine === "webgl" ? (
                <MapLibreRuntime {...runtimeProps} onUnsupported={retry} />
              ) : (
                <MapRuntime {...runtimeProps} />
              )}
            </Suspense>
          </MapBoundary>
          <div className="map-buttons">
            <button onClick={() => run("fit")} aria-label="Enquadrar Canoas">
              <Maximize size={18} />
            </button>
            <button
              onClick={() => run("route")}
              disabled={
                !selected.features.length &&
                (!ids.length || !selectedStops(data, ids).features.length)
              }
              aria-label="Enquadrar linhas selecionadas"
            >
              <Navigation size={18} />
            </button>
            <button
              onClick={() => run("locate")}
              aria-label="Localizar minha posição"
            >
              <LocateFixed size={18} />
            </button>
            <button onClick={retry} aria-label="Reiniciar mapa">
              <RefreshCw size={18} />
            </button>
          </div>
          <div className="map-legend">
            <strong>
              <MapPin size={14} />
              Canoas, RS
            </strong>
            <span>
              {theme === "densidade-paradas" ? "Paradas/km² · referência" :
                theme === "cobertura-paradas" ? "Área até 300 m (%) · referência" :
                (theme === "setores" ? "Setores 2022" : "Bairros oficiais") + " · habitantes/km²"}
            </span>
            <span className="density-scale">
              0 <i style={theme.includes("paradas")?{background:"linear-gradient(90deg,#fcf0dc,#e2ecd9,#a4d1b4,#4b9a86,#176557)"}:undefined}/> {theme==="densidade-paradas"?"≥ 20":theme==="cobertura-paradas"?"≥ 75%":"≥ 20 mil"}
            </span>
            {theme.includes("paradas")&&<span>{theme==="densidade-paradas"?"Classes: 0 · 5 · 10 · 20":"Classes: 0 · 25 · 50 · 75%"}. Cinza: sem dados. Amostra; não comprova atendimento.</span>}
            <span>
              Contorno: união dos bairros; não é limite municipal homologado.
            </span>
            {ids.slice(0, 5).map((id) => (
              <span key={id} className="legend-route">
                <i style={{ background: routeColor(id) }} />
                {id.replace(/^0+/, "")} ·{" "}
                {missing.includes(id)
                  ? "geometria pendente"
                  : "percurso de referência"}
              </span>
            ))}
            {ids.length > 5 && (
              <span>+ {ids.length - 5} linhas selecionadas</span>
            )}
          </div>
          <div
            className={"map-load-state " + status}
            role="status"
            data-testid="map-status"
          >
            {message}
            {status === "error" && (
              <button onClick={retry}>Tentar novamente</button>
            )}
          </div>
        </div>
        {!selectedRouteIds && !compact && (
          <aside className="map-route-panel">
            <h3>Linhas no mapa</h3>
            <p>
              {available} de {data.network.routes.length} linhas com geometria
              disponível.
            </p>
            <div className="search">
              <Search size={16} />
              <input
                aria-label="Buscar linha no mapa"
                placeholder="Código, bairro ou destino"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <button
              className="clear-routes"
              disabled={!ids.length}
              onClick={() => setLocalIds([])}
            >
              Limpar seleção ({ids.length})
            </button>
            <div className="map-route-list">
              {visible.map((r) => {
                const has = data.routeShapes?.features.some(
                  (f) => String(f.properties?.route_id) === r.id,
                );
                return (
                  <label key={r.id}>
                    <input
                      type="checkbox"
                      aria-label={"Desenhar linha " + r.code}
                      checked={ids.includes(r.id)}
                      onChange={(e) =>
                        setLocalIds((old) =>
                          e.target.checked
                            ? [...old, r.id]
                            : old.filter((id) => id !== r.id),
                        )
                      }
                    />
                    <i style={{ background: routeColor(r.id) }} />
                    <span>
                      <strong>
                        {r.code} · {r.name}
                      </strong>
                      <small>
                        {has
                          ? "Geometria de referência disponível"
                          : "Sem geometria validada"}
                      </small>
                    </span>
                  </label>
                );
              })}
            </div>
          </aside>
        )}
      </div>
      {missing.length > 0 && (
        <p className="map-data-notice" role="note">
          {missing.length === 1
            ? "A linha selecionada ainda não tem"
            : "As linhas selecionadas ainda não têm"}{" "}
          geometria disponível nesta base. Os horários e logradouros podem ser
          consultados; nenhum trajeto aproximado foi desenhado. Consulte também
          os horários e logradouros na página de linhas.
        </p>
      )}
      <p className="caption">
        Desenho por PMTiles local, sem chave de mapa. Os arquivos GeoJSON são
        alternativa automática em caso de falha de leitura.
      </p>
    </section>
  );
}
