import { describe, it, expect } from "vitest";
import {
  containsPoint,
  geometryBounds,
  selectedShapes,
  routeColor,
} from "./map-data";
import type { AppData } from "./types";
import type { Feature } from "geojson";
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
