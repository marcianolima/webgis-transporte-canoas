import { describe, it, expect } from "vitest";
import {
  containsPoint,
  geometryBounds,
  selectedShapes,
  routeColor,
  transportThemeColor,
  areaColor,
  tileStopVisible,
} from "./map-data";
import type { AppData } from "./types";
import type { Feature } from "geojson";
it("distingue zero, ausência e valores das análises territoriais de paradas",()=>{
  expect(transportThemeColor(null,"densidade-paradas")).toBe("#d6dcdf");
  expect(transportThemeColor(0,"densidade-paradas")).toBe("#fcf0dc");
  expect(transportThemeColor(25,"densidade-paradas")).toBe("#176557");
  expect(transportThemeColor(50,"cobertura-paradas")).toBe("#4b9a86");
  expect(areaColor({BAIRRO:"SYNTHETIC"},"cobertura-paradas",{SYNTHETIC:{stops_per_km2:10,covered_area_pct:80}})).toBe("#176557");
});
it("respeita bairro/busca e linhas também nas paradas desenhadas pelos tiles",()=>{
  const point={stop_id:"SYNTHETIC-A",route_ids_csv:"1,2"};
  expect(tileStopVisible(point,[],new Set(["SYNTHETIC-B"])) ).toBe(false);
  expect(tileStopVisible(point,[],new Set())).toBe(false);
  expect(tileStopVisible(point,["2"],new Set(["SYNTHETIC-A"]))).toBe(true);
  expect(tileStopVisible(point,["3"],new Set(["SYNTHETIC-A"]))).toBe(false);
});
// Geometria SYNTHETIC isolada de teste, nunca publicada na base real.
const line: Feature = {
  type: "Feature",
  properties: { route_id: "SYNTHETIC" },
  geometry: {
    type: "LineString",
    coordinates: [
      [-51.19, -29.91],
      [-51.18, -29.9],
    ],
  },
};
describe("seleção e geometria do mapa", () => {
  it("calcula enquadramento e mantém vazio sem geometria", () => {
    expect(geometryBounds([line])).toEqual([-51.19, -29.91, -51.18, -29.9]);
    expect(geometryBounds([])).toBeNull();
  });
  it("filtra uma ou várias linhas sem inventar percursos", () => {
    const data = {
      routeShapes: { type: "FeatureCollection", features: [line] },
    } as AppData;
    expect(selectedShapes(data, ["SYNTHETIC"]).features).toHaveLength(1);
    expect(selectedShapes(data, ["MISSING"]).features).toHaveLength(0);
    expect(routeColor("SYNTHETIC")).toBe(routeColor("SYNTHETIC"));
  });
  it("respeita buracos na consulta espacial", () => {
    const geometry = {
      type: "Polygon" as const,
      coordinates: [
        [
          [0, 0],
          [4, 0],
          [4, 4],
          [0, 4],
          [0, 0],
        ],
        [
          [1, 1],
          [2, 1],
          [2, 2],
          [1, 2],
          [1, 1],
        ],
      ],
    };
    expect(containsPoint(geometry, [3, 3])).toBe(true);
    expect(containsPoint(geometry, [1.5, 1.5])).toBe(false);
    expect(containsPoint(geometry, [5, 5])).toBe(false);
  });
});
