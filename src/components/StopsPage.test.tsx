import { afterEach, describe, it, expect, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import StopsPage from "./StopsPage";
import type { AppData } from "../types";
vi.mock("./TransportMap", () => ({
  default: () => <div>Mapa de teste isolado</div>,
}));
const fixture = {
  network: {
    routes: [
      { id: "05000", code: "5000", name: "SYNTHETIC A" },
      { id: "05001", code: "5001", name: "SYNTHETIC B" },
    ],
  },
  territory: { neighborhoods: [{ name: "SYNTHETIC CENTRO" }] },
  stops: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {
          stop_id: "11",
          name: "SYNTHETIC PARADA A",
          route_ids: ["05000"],
          neighborhood: "SYNTHETIC CENTRO",
        },
        geometry: { type: "Point", coordinates: [-51.19, -29.9] },
      },
      {
        type: "Feature",
        properties: {
          stop_id: "12",
          name: "SYNTHETIC PARADA B",
          route_ids: ["05001"],
          neighborhood: "SYNTHETIC OUTRO",
        },
        geometry: { type: "Point", coordinates: [-51.18, -29.91] },
      },
    ],
  },
} as unknown as AppData;
afterEach(cleanup);
describe("consulta de paradas reais normalizadas", () => {
  it("identifica fonte TACOM e filtra por linha sem links OSM inventados", () => {
    render(<StopsPage data={fixture} />);
    expect(screen.getByText("SYNTHETIC PARADA A")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Linha das paradas"), {
      target: { value: "05000" },
    });
    expect(screen.getByText("SYNTHETIC PARADA A")).toBeTruthy();
    expect(screen.queryByText("SYNTHETIC PARADA B")).toBeNull();
    expect(screen.queryByText("Identificador OSM")).toBeNull();
  });
  it("combina bairro e pesquisa por identificador", () => {
    render(<StopsPage data={fixture} />);
    fireEvent.change(screen.getByLabelText("Bairro das paradas"), {
      target: { value: "SYNTHETIC CENTRO" },
    });
    fireEvent.change(screen.getByLabelText("Buscar ponto"), {
      target: { value: "12" },
    });
    expect(screen.getByRole("status").textContent).toContain("Nenhuma parada");
  });
});
