import { useMemo, useRef, useState } from "react";
import { ArrowDownToLine, MapPin, Search, TriangleAlert } from "lucide-react";
import type { AppData } from "../types";
import { brDate, csv, download, number } from "../data";
import { stopRoutes } from "../map-data";
import TransportMap from "./TransportMap";
export default function StopsPage({ data }: { data: AppData }) {
  const [query, setQuery] = useState(""),
    [line, setLine] = useState(""),
    [neighborhood, setNeighborhood] = useState(""),
    [page, setPage] = useState(0),
    [focused, setFocused] = useState("");
  const mapNode = useRef<HTMLDivElement>(null);
  const filtered = useMemo(
    () =>
      data.stops.features.filter((f) => {
        const p = f.properties || {};
        const text = [
          p.stop_id,
          p.name,
          p.siu,
          p.neighborhood,
          ...stopRoutes(f),
        ]
          .join(" ")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase();
        return (
          (!line || stopRoutes(f).includes(line)) &&
          (!neighborhood || p.neighborhood === neighborhood) &&
          text.includes(
            query
              .normalize("NFD")
              .replace(/[\u0300-\u036f]/g, "")
              .toLowerCase(),
          )
        );
      }),
    [data.stops, query, line, neighborhood],
  );
  const mapData = useMemo(
    () => ({
      ...data,
      stops: { type: "FeatureCollection" as const, features: filtered },
    }),
    [data, filtered],
  );
  const rows = filtered.slice(page * 40, (page + 1) * 40);
  const pages = Math.max(1, Math.ceil(filtered.length / 40));
  const change = (setter: (v: string) => void, value: string) => {
    setter(value);
    setPage(0);
    setFocused("");
  };
  const exports = filtered.map((f) => ({
    id: f.properties?.stop_id,
    nome: f.properties?.name,
    bairro: f.properties?.neighborhood,
    linhas: stopRoutes(f)
      .map((id) => id.replace(/^0+/, ""))
      .join(", "),
    longitude: f.geometry.type === "Point" ? f.geometry.coordinates[0] : null,
    latitude: f.geometry.type === "Point" ? f.geometry.coordinates[1] : null,
    fonte: f.properties?.source_name,
    origem: f.properties?.source_url,
    obtido_em: f.properties?.fetched_at,
  }));
  return (
    <>
      <div className="notice warning">
        <TriangleAlert size={18} />
        <span>
          {data.stops.features.length
            ? `${number(data.stops.features.length)} paradas de referência da TACOM com coordenadas e vínculos por ID. A amostra é parcial; atendimento, sentidos, sequência e vigência operacional ainda precisam de homologação.`
            : "Cadastro geográfico municipal ainda indisponível. A ausência de pontos não significa ausência de atendimento."}
        </span>
      </div>
      <section className="panel stops-filter-panel">
        <h2>Consultar paradas</h2>
        <div className="stops-filters">
          <label className="search">
            <Search size={16} />
            <input
              aria-label="Buscar ponto"
              placeholder="Nome, código ou logradouro"
              value={query}
              onChange={(e) => change(setQuery, e.target.value)}
            />
          </label>
          <label>
            Linha
            <select
              aria-label="Linha das paradas"
              value={line}
              onChange={(e) => change(setLine, e.target.value)}
            >
              <option value="">Todas as linhas</option>
              {data.network.routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.code} · {r.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Bairro
            <select
              aria-label="Bairro das paradas"
              value={neighborhood}
              onChange={(e) => change(setNeighborhood, e.target.value)}
            >
              <option value="">Todos os bairros</option>
              {data.territory.neighborhoods.map((n) => (
                <option key={n.name}>{n.name}</option>
              ))}
            </select>
          </label>
        </div>
        <p className="caption">
          {number(filtered.length)} de {number(data.stops.features.length)}{" "}
          pontos na consulta. O vínculo entre bases é por código exato, sujeito
          à conferência da variante.
        </p>
      </section>
      <div ref={mapNode} className="stops-map-anchor">
        <TransportMap
          data={mapData}
          compact
          selectedRouteIds={line ? [line] : []}
          focusedStopId={focused}
        />
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Pontos disponíveis</h2>
            <p>Cadastro TACOM / SIU Mobile · referência geográfica</p>
          </div>
          <div className="export-actions">
            <button
              disabled={!filtered.length}
              onClick={() =>
                download("paradas-canoas.csv", csv(exports), "text/csv")
              }
            >
              <ArrowDownToLine size={15} />
              CSV
            </button>
            <button
              disabled={!filtered.length}
              onClick={() =>
                download(
                  "paradas-canoas.geojson",
                  JSON.stringify({
                    type: "FeatureCollection",
                    features: filtered,
                  }),
                )
              }
            >
              GeoJSON
            </button>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Identificador TACOM</th>
                <th>Nome informado</th>
                <th>Bairro</th>
                <th>Linhas por código</th>
                <th>Consulta da fonte</th>
                <th>Mapa</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((f) => (
                <tr key={String(f.properties?.stop_id)}>
                  <td>
                    {f.properties?.stop_id}
                    <small className="cell-detail">
                      {f.properties?.siu || "Sem código SIU"}
                    </small>
                  </td>
                  <td>{f.properties?.name || "Sem nome publicado"}</td>
                  <td>{f.properties?.neighborhood || "Área de borda"}</td>
                  <td>
                    <span className="stop-route-codes">
                      {stopRoutes(f)
                        .map((id) => id.replace(/^0+/, ""))
                        .join(" · ")}
                    </span>
                  </td>
                  <td>{brDate(f.properties?.fetched_at, true)}</td>
                  <td>
                    <button
                      aria-label={
                        "Ver parada " + f.properties?.stop_id + " no mapa"
                      }
                      onClick={() => {
                        setFocused(String(f.properties?.stop_id));
                        mapNode.current?.scrollIntoView({
                          block: "start",
                          behavior: "smooth",
                        });
                      }}
                    >
                      <MapPin size={15} />
                      Ver
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!filtered.length && (
          <p role="status">Nenhuma parada publicada corresponde aos filtros.</p>
        )}
        <div className="pagination">
          <button disabled={!page} onClick={() => setPage((v) => v - 1)}>
            Anterior
          </button>
          <span>
            Página {page + 1} de {pages}
          </span>
          <button
            disabled={page + 1 >= pages}
            onClick={() => setPage((v) => v + 1)}
          >
            Próxima
          </button>
        </div>
        <p className="caption">
          As coordenadas foram consultadas individualmente ou por proximidade e
          cruzadas com IDs das listas de linhas municipais. Não são estimativas
          nem posições de ônibus. A cobertura desta amostra não representa o
          cadastro completo da rede.
        </p>
      </section>
    </>
  );
}
