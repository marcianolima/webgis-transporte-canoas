/* Ícones PNG sem dependências externas, com desenho no centro da safe area maskable. */
import { mkdirSync, writeFileSync } from "node:fs";
import { deflateSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
const target = fileURLToPath(new URL("../public/icons/", import.meta.url));
mkdirSync(target, { recursive: true });
function crc32(bytes) {
  let crc = 0xffffffff;
  for (const b of bytes) {
    crc ^= b;
    for (let j = 0; j < 8; j++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(name, data) {
  const type = Buffer.from(name);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4);
  checksum.writeUInt32BE(crc32(Buffer.concat([type, data])));
  return Buffer.concat([length, type, data, checksum]);
}
function icon(size) {
  const rgba = Buffer.alloc((size * 4 + 1) * size);
  const inside = (x, y, a, b, w, h, r) => {
    const nx = Math.max(a + r, Math.min(x, a + w - r));
    const ny = Math.max(b + r, Math.min(y, b + h - r));
    return (x - nx) ** 2 + (y - ny) ** 2 <= r * r;
  };
  for (let y = 0; y < size; y++) {
    const row = y * (size * 4 + 1);
    for (let x = 0; x < size; x++) {
      const u = (x + 0.5) / size, v = (y + 0.5) / size;
      let rgb = [18, 62, 66];
      // Corpo central do ônibus, janelas e faróis. Todo elemento informativo
      // fica na região central para suportar recorte circular no Android.
      if (inside(u, v, 0.285, 0.22, 0.43, 0.56, 0.060)) rgb = [184, 220, 135];
      if (inside(u, v, 0.31, 0.25, 0.38, 0.30, 0.027)) rgb = [235, 246, 227];
      if (u > 0.49 && u < 0.51 && v > 0.25 && v < 0.55) rgb = [18, 62, 66];
      if (u > 0.31 && u < 0.69 && v > 0.565 && v < 0.582) rgb = [18, 62, 66];
      for (const c of [0.37, 0.63]) {
        if ((u - c) ** 2 + (v - 0.685) ** 2 < 0.024 ** 2) rgb = [18, 62, 66];
        if (u > c - 0.021 && u < c + 0.021 && v > 0.78 && v < 0.825) rgb = [235, 246, 227];
      }
      const at = row + 1 + x * 4;
      rgba[at] = rgb[0];
      rgba[at + 1] = rgb[1];
      rgba[at + 2] = rgb[2];
      rgba[at + 3] = 255;
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([137,80,78,71,13,10,26,10]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(rgba, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}
for (const size of [192, 512]) writeFileSync(join(target, "icon-" + size + ".png"), icon(size));
