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
  ];
  const values = await Promise.all(
    names.map(async (name) => {
      const r = await fetch(base + "data/" + name);
      if (!r.ok) throw new Error("Não foi possível carregar " + name);
      return r.json();
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
  };
}
