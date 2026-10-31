import { afterEach, describe, it, expect, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import TransportMap from "./TransportMap";
import type { AppData } from "../types";
vi.mock("./MapRuntime", () => ({
  default: ({ style }: { style: { routeIds: string[] } }) => (
    <div data-testid="selected-routes">{style.routeIds.join(",")}</div>
  ),
}));
vi.mock("./MapLibreRuntime", () => ({ default: () => <div>WebGL</div> }));
const fixture = {
  network: {
    routes: [{ id: "SYNTHETIC", code: "TEST", name: "SYNTHETIC fixture" }],
  },
  territory: { neighborhoods: [] },
  routeShapes: { type: "FeatureCollection", features: [] },
} as unknown as AppData;
afterEach(cleanup);
describe("controles cartográficos", () => {
  it("seleciona e limpa linha; informa geometria ausente", async () => {
    render(<TransportMap data={fixture} />);
    await screen.findByTestId("selected-routes");
    fireEvent.click(screen.getByLabelText("Desenhar linha TEST"));
    expect(screen.getByTestId("selected-routes").textContent).toBe("SYNTHETIC");
    expect(screen.getByRole("note").textContent).toContain(
      "nenhum trajeto aproximado",
    );
    expect(
      (
        screen.getByLabelText(
          "Enquadrar linhas selecionadas",
        ) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    fireEvent.click(screen.getByText("Limpar seleção (1)"));
    expect(screen.getByTestId("selected-routes").textContent).toBe("");
  });
  it("habilita enquadramento somente quando existe geometria", async () => {
    const shapes = {
      ...fixture,
      routeShapes: {
        type: "FeatureCollection" as const,
        features: [
          {
            type: "Feature" as const,
            properties: { route_id: "SYNTHETIC" },
            geometry: {
              type: "LineString" as const,
              coordinates: [
                [-51.19, -29.91],
                [-51.18, -29.9],
              ],
            },
          },
        ],
      },
    };
    render(<TransportMap data={shapes} selectedRouteIds={["SYNTHETIC"]} />);
    await screen.findByTestId("selected-routes");
    expect(
      (
        screen.getByLabelText(
          "Enquadrar linhas selecionadas",
        ) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
    expect(screen.queryByRole("note")).toBeNull();
  });
  it("busca por nome e não descarta seleção ao filtrar", async () => {
    render(<TransportMap data={fixture} />);
    await screen.findByTestId("selected-routes");
    fireEvent.click(screen.getByLabelText("Desenhar linha TEST"));
    fireEvent.change(screen.getByLabelText("Buscar linha no mapa"), {
      target: { value: "ausente" },
    });
    expect(screen.queryByLabelText("Desenhar linha TEST")).toBeNull();
    expect(screen.getByTestId("selected-routes").textContent).toBe("SYNTHETIC");
  });
});
