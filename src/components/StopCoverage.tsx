import { ArrowDownToLine } from "lucide-react";
import type { AppData } from "../types";
import { brDate, csv, download, number } from "../data";

const statusNames: Record<string, string> = {
  pending: "Consulta pendente",
  no_coordinates: "Fonte sem coordenadas",
  outside_reference_area: "Fora da área de referência",
  coordinate_conflict: "Coordenadas em conflito",
  lookup_failed: "Falha de consulta",
};

export default function StopCoverage({ data, onSelectLine }: {
  data: AppData;
  onSelectLine?: (id: string) => void;
}) {
  const inventory = data.stopInventory;
  if (!inventory) return null;
  const routes = new Map(data.network.routes.map(r => [r.id, r]));
  const rows = [...inventory.routes].sort((a, b) =>
    b.unlocated_stop_ids - a.unlocated_stop_ids || a.route_id.localeCompare(b.route_id),
  );
  const missing = inventory.stops.filter(s => s.status !== "located");
  const exportLines = () => download("completude-paradas-por-linha.csv", csv(rows.map(r => ({
    linha: routes.get(r.route_id)?.code ?? r.route_id,
    ids_na_fonte: r.known_stop_ids,
    ids_localizados: r.located_stop_ids,
    ids_sem_posicao: r.unlocated_stop_ids,
    localizacao_pct: r.localization_pct,
    origem: r.source_url,
    consultado_em: r.fetched_at,
  }))), "text/csv");
  const exportMissing = () => download("paradas-sem-posicao.csv", csv(missing.map(s => ({
    id: s.stop_id,
    nome: s.name,
    linhas: s.route_ids.join(", "),
    situacao: statusNames[s.status] ?? s.status,
  }))), "text/csv");
  return (
    <section className="panel stop-coverage" aria-labelledby="stop-coverage-title">
      <div className="panel-title">
        <div>
          <h2 id="stop-coverage-title">Completude das paradas consultadas</h2>
          <p>IDs das listas TACOM · consolidação em {brDate(inventory.generated_at, true)}</p>
        </div>
        <button onClick={exportLines}><ArrowDownToLine size={15} />CSV por linha</button>
      </div>
      <div className="stop-coverage-metrics">
        <div>
          <span>IDs com posição publicada</span>
          <strong>{number(inventory.located_stop_ids)} <small>de {number(inventory.source_stop_ids)}</small></strong>
        </div>
        <div>
          <span>Localização no recorte</span>
          <strong>{inventory.localization_pct == null ? "Não disponível" : number(inventory.localization_pct, 1) + "%"}</strong>
        </div>
        <div><span>IDs sem posição no mapa</span><strong>{number(inventory.unlocated_stop_ids)}</strong></div>
      </div>
      <p className="caption">
        Foram obtidas listas de {number(inventory.source_lines_successful)} das {number(inventory.catalogue_routes)} linhas do catálogo.
        O percentual mede localização dos IDs conhecidos desse recorte; não mede cobertura do município nem serviço realizado.
        Áreas sem pontos podem indicar dados ainda ausentes.
      </p>
      <details>
        <summary>Conferir completude por linha</summary>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Linha</th><th>IDs na fonte</th><th>Localizados</th><th>Sem posição</th><th>Localização</th></tr></thead>
            <tbody>{rows.map(row => {
              const route = routes.get(row.route_id);
              return (
                <tr key={row.route_id}>
                  <td>{onSelectLine ? (
                    <button onClick={() => onSelectLine(row.route_id)} aria-label={`Consultar paradas da linha ${route?.code ?? row.route_id}`}>
                      {route?.code ?? row.route_id} · {route?.name ?? "Linha de referência"}
                    </button>
                  ) : <>{route?.code ?? row.route_id} · {route?.name}</>}</td>
                  <td>{number(row.known_stop_ids)}</td>
                  <td>{number(row.located_stop_ids)}</td>
                  <td>{number(row.unlocated_stop_ids)}</td>
                  <td>{row.localization_pct == null ? "Sem IDs na lista" : number(row.localization_pct, 1) + "%"}</td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
      </details>
      {missing.length > 0 && (
        <details>
          <summary>IDs sem posição: motivos e exportação</summary>
          <p className="caption">Nenhuma coordenada ou bairro foi estimado para estes IDs. Divergências territoriais ficam fora do mapa até revisão.</p>
          <ul>{Object.entries(inventory.status_counts)
            .filter(([status]) => status !== "located")
            .map(([status, count]) => <li key={status}>{statusNames[status] ?? status}: {number(count)}</li>)}</ul>
          <button onClick={exportMissing}><ArrowDownToLine size={15} />Exportar IDs sem posição</button>
        </details>
      )}
    </section>
  );
}
