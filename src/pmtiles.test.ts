import { afterEach, describe, it, expect, vi } from "vitest";
import { ResilientSource } from "./pmtiles";
// Apenas bytes SYNTHETIC para validar transporte HTTP; não são um arquivo cartográfico publicado.
const blob = new TextEncoder().encode("PMTilesSYNTHETIC_TEST_BYTES")
  .buffer as ArrayBuffer;
afterEach(() => vi.unstubAllGlobals());
describe("leitura resiliente de PMTiles", () => {
  it("mantém leitura Range quando o servidor a suporta", async () => {
    const mock = vi
      .fn()
      .mockResolvedValue(new Response(blob.slice(0, 7), { status: 206 }));
    vi.stubGlobal("fetch", mock);
    const source = new ResilientSource("https://example.invalid/test.pmtiles");
    const value = await source.getBytes(0, 7);
    expect(new TextDecoder().decode(value.data)).toBe("PMTiles");
    expect(mock).toHaveBeenCalledTimes(1);
  });
  it("servidor sem Range usa um arquivo completo cacheado e fatia os intervalos", async () => {
    const mock = vi.fn().mockResolvedValue(new Response(blob));
    vi.stubGlobal("fetch", mock);
    const source = new ResilientSource("https://example.invalid/test.pmtiles");
    expect(new TextDecoder().decode((await source.getBytes(0, 7)).data)).toBe(
      "PMTiles",
    );
    expect(new TextDecoder().decode((await source.getBytes(7, 9)).data)).toBe(
      "SYNTHETIC",
    );
    expect(mock).toHaveBeenCalledTimes(2);
  });
  it("rejeita arquivo completo acima do limite de 20 MB", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(blob, { headers: { "content-length": "20000001" } }),
        ),
    );
    await expect(
      new ResilientSource("https://example.invalid/test.pmtiles").getBytes(
        0,
        7,
      ),
    ).rejects.toThrow("20 MB");
  });
  it("cancelamento não dispara uma nova transferência completa", async () => {
    const controller = new AbortController();
    controller.abort();
    const mock = vi
      .fn()
      .mockRejectedValue(new DOMException("aborted", "AbortError"));
    vi.stubGlobal("fetch", mock);
    await expect(
      new ResilientSource("https://example.invalid/test.pmtiles").getBytes(
        0,
        7,
        controller.signal,
      ),
    ).rejects.toThrow("aborted");
    expect(mock).toHaveBeenCalledTimes(1);
  });
});
