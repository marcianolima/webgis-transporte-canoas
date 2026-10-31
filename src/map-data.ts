import type { Feature, FeatureCollection, Geometry, Position } from "geojson";
import type { AppData } from "./types";
export const routePalette = [
  "#1463b5",
  "#cf493f",
  "#6b46a6",
  "#008773",
  "#b36512",
  "#b33f80",
  "#507a22",
  "#4c6577",
];
export function routeColor(id: string) {
  let hash = 0;
  for (const c of id) hash = (hash * 31 + c.charCodeAt(0)) >>> 0;
  return routePalette[hash % routePalette.length];
}
export function densityColor(value: number) {
  return value >= 20000
    ? "#176557"
    : value >= 10000
      ? "#4b9a86"
      : value >= 3000
        ? "#a4d1b4"
        : "#d7ead6";
}
export function geometryBounds(
  features: Feature[],
): [number, number, number, number] | null {
  let w = Infinity,
    s = Infinity,
    e = -Infinity,
    n = -Infinity;
  const walk = (p: any) => {
    if (!Array.isArray(p)) return;
    if (typeof p[0] === "number" && typeof p[1] === "number") {
      if (Number.isFinite(p[0]) && Number.isFinite(p[1])) {
        w = Math.min(w, p[0]);
        e = Math.max(e, p[0]);
        s = Math.min(s, p[1]);
        n = Math.max(n, p[1]);
      }
    } else p.forEach(walk);
  };
  for (const f of features) {
    if (f.geometry && "coordinates" in f.geometry) walk(f.geometry.coordinates);
  }
  return Number.isFinite(w) ? [w, s, e, n] : null;
}
export function selectedShapes(
  data: AppData,
  ids: string[],
): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: (data.routeShapes?.features || []).filter((f) =>
      ids.includes(String(f.properties?.route_id)),
    ),
  };
}
function inRing(p: Position, ring: Position[]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i],
      b = ring[j];
    if (
      a[1] > p[1] !== b[1] > p[1] &&
      p[0] < ((b[0] - a[0]) * (p[1] - a[1])) / (b[1] - a[1]) + a[0]
    )
      inside = !inside;
  }
  return inside;
}
export function containsPoint(g: Geometry | null, p: Position): boolean {
  if (!g) return false;
  const polygon = (rings: Position[][]) =>
    !!rings.length &&
    inRing(p, rings[0]) &&
    !rings.slice(1).some((r) => inRing(p, r));
  if (g.type === "Polygon") return polygon(g.coordinates);
  if (g.type === "MultiPolygon") return g.coordinates.some(polygon);
  return false;
}
export function findArea(data: AppData, theme: string, point: Position) {
  return (
    theme === "setores" ? data.sectors : data.neighborhoods
  ).features.find((f) => containsPoint(f.geometry, point));
}
export const emptyCollection: FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};
