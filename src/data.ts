import type { AppData, Departure, Vehicle } from "./types";
export const base = import.meta.env.BASE_URL;
export function brDate(value: string | null | undefined, time = false) {
  if (!value) return "Não disponível";
  const d = new Date(value.length === 10 ? value + "T12:00:00-03:00" : value);
  return Number.isNaN(d.getTime())
    ? "Data inválida"
    : new Intl.DateTimeFormat("pt-BR", {
        timeZone: "America/Sao_Paulo",
        dateStyle: "short",
        ...(time ? { timeStyle: "short" as const } : {}),
      }).format(d);
}
export const number = (n: number | null | undefined, digits = 0) =>
  n == null
    ? "Não disponível"
    : new Intl.NumberFormat("pt-BR", { maximumFractionDigits: digits }).format(
        n,
      );
export function freshness(
  value: string | undefined,
  maxHours = 48,
  now = Date.now(),
) {
  if (!value) return "unavailable";
  const age = (now - Date.parse(value)) / 3600000;
  return !Number.isFinite(age) || age < -0.05
    ? "invalid"
    : age > maxHours
      ? "stale"
      : "recent";
}
export function currentVehicles(vehicles: Vehicle[], now = Date.now()) {
  return vehicles.filter(
    (v) =>
      Number.isFinite(v.latitude) &&
      Number.isFinite(v.longitude) &&
      Date.parse(v.observed_at) <= now + 30_000 &&
      now - Date.parse(v.observed_at) <= 180_000,
  );
}
export function groupSchedules(rows: Departure[]) {
  const map = new Map<string, Departure[]>();
  for (const d of rows) {
    const key = d.direction;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(d);
  }
  return [...map].map(([direction, items]) => ({
    direction,
    items: items.sort((a, b) => a.sequence - b.sequence),
  }));
}
export function headways(rows: Departure[]) {
  return groupSchedules(rows).flatMap((g) =>
    g.items
      .slice(1)
      .map((v, i) => v.service_minute - g.items[i].service_minute)
      .filter((v) => v >= 0),
  );
}
export function filterDepartures(
  rows: Departure[],
  route: string,
  date: string,
  direction = "",
  start = 0,
  end = 2880,
) {
  return rows.filter(
    (d) =>
      (!route || d.route_id === route) &&
      d.date === date &&
      (!direction || d.direction === direction) &&
      d.service_minute >= start &&
      d.service_minute < end,
  );
}
export function download(
  name: string,
  content: string,
  type = "application/json",
) {
  const blob = new Blob(["\uFEFF" + content], {
    type: type + ";charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
export function csv(rows: Record<string, unknown>[]) {
  if (!rows.length) return "";
  const fields = Object.keys(rows[0]);
  const safe = (v: unknown) => {
    let s = String(v ?? "");
    if (/^[=+@-]/.test(s)) s = "'" + s;
    return '"' + s.replaceAll('"', '""') + '"';
  };
  return (
    fields.map(safe).join(";") +
    "\r\n" +
    rows.map((row) => fields.map((k) => safe(row[k])).join(";")).join("\r\n")
  );
}
export async function loadData(): Promise<AppData> {
  const names = [
    "network.json",
    "catalogue.json",
    "territory.json",
    "bairros-oficiais.geojson",
    "censo2022-setores.geojson",
    "stops.geojson",
    "boundary.geojson",
    "vehicles.json",
    "map-manifest.json",
    "route-shapes.geojson",
    "stop-inventory.json",
  ];
  const values = await Promise.all(
    names.map(async (name) => {
      const optional =
        name === "map-manifest.json" || name === "route-shapes.geojson" || name === "stop-inventory.json";
      try {
        const response = await fetch(base + "data/" + name);
        if (!response.ok) throw new Error("Não foi possível carregar " + name);
        const document = await response.json();
        if (
          name === "map-manifest.json" &&
          (!/^[\w-]+\.pmtiles$/.test(document.file) ||
            !/^[a-f0-9]{64}$/.test(document.sha256) ||
            !document.layers)
        )
          throw new Error("Manifesto cartográfico incompatível");
        if (
          name === "route-shapes.geojson" &&
          (document.type !== "FeatureCollection" ||
            !Array.isArray(document.features))
        )
          throw new Error("Geometria cartográfica incompatível");
        if (name === "stop-inventory.json" &&
            (document.schema_version !== 1 || !Array.isArray(document.routes) ||
             !Array.isArray(document.stops) || !Number.isInteger(document.source_stop_ids) ||
             document.municipality_code !== "4304606" || document.city_id !== "4" ||
             !Number.isInteger(document.located_stop_ids) || document.located_stop_ids < 0 ||
             !Number.isInteger(document.unlocated_stop_ids) || document.unlocated_stop_ids < 0 ||
             document.source_stop_ids !== document.stops.length ||
             document.located_stop_ids + document.unlocated_stop_ids !== document.source_stop_ids ||
             !document.routes.every((r:any)=>typeof r.route_id === "string" && Number.isInteger(r.known_stop_ids) && Number.isInteger(r.located_stop_ids) && Number.isInteger(r.unlocated_stop_ids)) ||
             !document.stops.every((s:any)=>typeof s.stop_id === "string" && Array.isArray(s.route_ids) && s.route_ids.every((id:unknown)=>typeof id === "string") && typeof s.status === "string") ||
             !document.status_counts || typeof document.status_counts !== "object" ||
             !Number.isInteger(document.source_lines_successful) || !Number.isInteger(document.catalogue_routes)))
          throw new Error("Inventário de paradas incompatível");
        return document;
      } catch (error) {
        if (name === "vehicles.json" && typeof navigator !== "undefined" && !navigator.onLine) {
          return { status: "unavailable", generated_at: null, vehicles: [],
            message: "Sem rede: não é possível consultar posições atuais de veículos." };
        }
        if (!optional) throw error;
        return name === "map-manifest.json" || name === "stop-inventory.json"
          ? undefined
          : { type: "FeatureCollection", features: [] };
      }
    }),
  );
  const [
    network,
    catalogue,
    territory,
    neighborhoods,
    sectors,
    stops,
    boundary,
    vehicles,
    mapManifest,
    routeShapes,
    stopInventory,
  ] = values;
  if (
    network.schema_version !== 1 ||
    !Array.isArray(network.routes) ||
    !Array.isArray(network.departures)
  )
    throw new Error("Formato de dados incompatível");
  return {
    network,
    catalogue,
    territory,
    neighborhoods,
    sectors,
    stops,
    boundary,
    vehicles,
    mapManifest,
    routeShapes,
    stopInventory,
  };
}
