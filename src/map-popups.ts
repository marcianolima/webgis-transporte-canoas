import type { Feature } from "geojson";
import { brDate } from "./data";
import { stopRoutes } from "./map-data";
export function stopPopup(feature: Feature): HTMLElement {
  const p = feature.properties || {},
    node = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = p.name || "Parada " + p.stop_id;
  const lines = document.createElement("p");
  lines.textContent =
    "Linhas por código: " +
    (stopRoutes(feature)
      .map((id) => id.replace(/^0+/, ""))
      .join(", ") || "Vínculo não informado");
  const meta = document.createElement("p");
  meta.textContent =
    (p.neighborhood || "Bairro não identificado") +
    " · ID " +
    (p.stop_id || feature.id);
  const source = document.createElement("p");
  source.textContent =
    (p.source_name || p.source || "Fonte não informada") +
    " · consulta " +
    brDate(p.fetched_at, true);
  const limit = document.createElement("small");
  limit.textContent =
    "Referência do cadastro da API. Atendimento, sentido e vigência sujeitos a conferência; não é previsão de chegada.";
  node.append(title, meta, lines, source, limit);
  return node;
}
