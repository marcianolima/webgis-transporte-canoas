import { FetchSource, PMTiles, Protocol, type RangeResponse } from "pmtiles";
import { VectorTile } from "@mapbox/vector-tile";
import Pbf from "pbf";
import L from "leaflet";
import { base } from "./data";
import { densityColor, routeColor } from "./map-data";

/** Leitura Range normal; servidores sem Range recebem uma única leitura completa, limitada. */
export class ResilientSource extends FetchSource {
  private complete?: Promise<ArrayBuffer>;
  async getBytes(
    offset: number,
    length: number,
    signal?: AbortSignal,
    etag?: string,
  ): Promise<RangeResponse> {
    if (this.complete)
      return { data: (await this.complete).slice(offset, offset + length) };
    try {
      return await super.getBytes(offset, length, signal, etag);
    } catch (error) {
      if (signal?.aborted) throw error;
      this.complete ??= fetch(this.url).then(async (response) => {
        if (!response.ok) throw Error("Arquivo PMTiles indisponível");
        const size = Number(response.headers.get("content-length") || 0);
        if (size > 20_000_000) throw Error("Arquivo PMTiles acima de 20 MB");
        const buffer = await response.arrayBuffer();
        if (
          buffer.byteLength > 20_000_000 ||
          new TextDecoder().decode(buffer.slice(0, 7)) !== "PMTiles"
        )
          throw Error("Arquivo PMTiles inválido");
        return buffer;
      });
      return { data: (await this.complete).slice(offset, offset + length) };
    }
  }
}
export function mapArchive(file = "transporte-canoas.pmtiles", sha?: string) {
  const location = new URL(base + "data/" + file, window.location.origin);
  if (sha) location.searchParams.set("v", sha.slice(0, 16));
  const url = location.href;
  // Uma instância por montagem: reiniciar também descarta falhas/cache da leitura anterior.
  return new PMTiles(new ResilientSource(url));
}
export function registerPMTiles(maplibre: {
  addProtocol: (name: string, fn: any) => void;
}) {
  if (!protocolRegistered) {
    maplibre.addProtocol("pmtiles", protocol.tile);
    protocolRegistered = true;
  }
}
const protocol = new Protocol();
let protocolRegistered = false;
export function attachArchiveToProtocol(file?: string, sha?: string) {
  const archive = mapArchive(file, sha);
  protocol.add(archive);
  return archive.source.getKey();
}
export interface TileStyle {
  theme: string;
  routeIds: string[];
  territorial: boolean;
  showStops?: boolean;
}
export class LocalVectorLayer extends L.GridLayer {
  private tileData = new Map<string, ReturnType<PMTiles["getZxy"]>>();
  constructor(
    private archive: PMTiles,
    private style: () => TileStyle,
    private ready: (count: number) => void,
    private failed: (error: unknown) => void,
  ) {
    super({
      tileSize: 256,
      maxNativeZoom: 20,
      minZoom: 8,
      maxZoom: 20,
      attribution: "GeoCanoas · IBGE Censo 2022 · PMTiles local",
      keepBuffer: 2,
    });
  }
  createTile(coords: L.Coords, done: L.DoneCallback) {
    const canvas = document.createElement("canvas");
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = 256 * ratio;
    canvas.height = 256 * ratio;
    canvas.style.width = "256px";
    canvas.style.height = "256px";
    const z = Math.min(coords.z, 13),
      factor = 2 ** (coords.z - z),
      x = Math.floor(coords.x / factor),
      y = Math.floor(coords.y / factor),
      key = `${z}/${x}/${y}`;
    if (!this.tileData.has(key)) {
      if (this.tileData.size >= 64)
        this.tileData.delete(this.tileData.keys().next().value!);
      this.tileData.set(key, this.archive.getZxy(z, x, y));
    }
    this.tileData
      .get(key)!
      .then((result) => {
        if (!result) {
          done(undefined, canvas);
          return;
        }
        const tile = new VectorTile(new Pbf(new Uint8Array(result.data)));
        const ctx = canvas.getContext("2d");
        if (!ctx) throw Error("Canvas 2D não disponível");
        ctx.scale(ratio, ratio);
        ctx.translate(
          -(coords.x - x * factor) * 256,
          -(coords.y - y * factor) * 256,
        );
        const style = this.style();
        let count = 0;
        for (const name of [
          style.theme === "setores" ? "setores" : "bairros",
          "limite",
          "linhas",
          "paradas",
        ]) {
          const layer = tile.layers[name];
          if (!layer) continue;
          for (let i = 0; i < layer.length; i++) {
            if (name === "paradas" && style.showStops === false) continue;
            const f = layer.feature(i),
              p = f.properties;
            if (
              name === "linhas" &&
              !style.routeIds.includes(String(p.route_id))
            )
              continue;
            if (
              name === "paradas" &&
              style.routeIds.length &&
              !style.routeIds.some((id) =>
                ("," + String(p.route_ids_csv || "") + ",").includes(
                  "," + id + ",",
                ),
              )
            )
              continue;
            const scale = (256 / f.extent) * factor;
            const geom = f.loadGeometry();
            ctx.beginPath();
            for (const ring of geom) {
              ring.forEach((point, j) => {
                if (j === 0) ctx.moveTo(point.x * scale, point.y * scale);
                else ctx.lineTo(point.x * scale, point.y * scale);
              });
              if (f.type === 3) ctx.closePath();
            }
            ctx.setLineDash([]);
            ctx.globalAlpha = 1;
            if (f.type === 3) {
              const density =
                Number(p.POPULACAO_2022 ?? p.pop ?? 0) /
                Math.max(0.001, Number(p.AREA_KM2 ?? p.area_km2 ?? 1));
              ctx.fillStyle = densityColor(density);
              ctx.globalAlpha =
                style.theme === "setores" || style.territorial ? 0.75 : 0.45;
              if (name !== "limite") ctx.fill("evenodd");
              ctx.globalAlpha = 1;
              ctx.strokeStyle =
                name === "limite"
                  ? "#163f43"
                  : style.theme === "setores"
                    ? "#f7faf6"
                    : "#3a6860";
              ctx.lineWidth =
                name === "limite"
                  ? 1.6
                  : style.theme === "setores"
                    ? 0.35
                    : 0.8;
              if (name === "limite") ctx.setLineDash([5, 4]);
              ctx.stroke();
            } else if (f.type === 2) {
              ctx.strokeStyle = routeColor(String(p.route_id));
              ctx.lineWidth = 4;
              ctx.lineJoin = "round";
              ctx.lineCap = "round";
              ctx.stroke();
            } else if (f.type === 1) {
              ctx.fillStyle = "#9f6a18";
              for (const ring of geom)
                for (const point of ring) {
                  ctx.beginPath();
                  ctx.arc(point.x * scale, point.y * scale, 4, 0, Math.PI * 2);
                  ctx.fill();
                }
            }
            count++;
          }
        }
        this.ready(count);
        done(undefined, canvas);
      })
      .catch((error) => {
        this.failed(error);
        done(error instanceof Error ? error : new Error(String(error)), canvas);
      });
    return canvas;
  }
}
