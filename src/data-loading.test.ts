import { afterEach, describe, it, expect, vi } from "vitest";
import { loadData } from "./data";
const empty = { type: "FeatureCollection", features: [] };
const respond = (url: string) =>
  new Response(
    JSON.stringify(
      url.endsWith("network.json")
        ? { schema_version: 1, routes: [], departures: [] }
        : empty,
    ),
  );
afterEach(() => vi.unstubAllGlobals());
describe("recuperação do carregamento cartográfico", () => {
  it("falha de rede em manifesto ou shapes preserva demais dados", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        /map-manifest|route-shapes/.test(url)
          ? Promise.reject(Error("SYNTHETIC rede indisponível"))
          : Promise.resolve(respond(url)),
      ),
    );
    const value = await loadData();
    expect(value.mapManifest).toBeUndefined();
    expect(value.routeShapes?.features).toHaveLength(0);
    expect(value.neighborhoods).toEqual(empty);
  });
  it("JSON inválido em recurso opcional não derruba a aplicação", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        Promise.resolve(
          /map-manifest|route-shapes/.test(url)
            ? new Response("<html>erro SYNTHETIC</html>")
            : respond(url),
        ),
      ),
    );
    expect((await loadData()).mapManifest).toBeUndefined();
  });
  it("continua informando falha quando o cadastro essencial não carrega", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        Promise.resolve(
          url.endsWith("network.json")
            ? new Response("", { status: 503 })
            : respond(url),
        ),
      ),
    );
    await expect(loadData()).rejects.toThrow("network.json");
  });
});
