/* Checagens de publicação PWA reais após npm run build. */
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
const file = (path) => readFileSync(new URL("../dist/" + path, import.meta.url));
const manifest = JSON.parse(file("manifest.webmanifest").toString("utf8"));
assert.equal(manifest.start_url, "./#geral");
assert.equal(manifest.scope, "./");
assert.equal(manifest.display, "standalone");
for (const n of [192, 512]) {
  const icon = file("icons/icon-" + n + ".png");
  assert.equal(icon.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.equal(icon.readUInt32BE(16), n);
  assert.equal(icon.readUInt32BE(20), n);
}
const html = file("index.html").toString("utf8");
assert.match(html, /rel="manifest"/);
assert.match(html, /\/webgis-transporte-canoas\/manifest\.webmanifest/);
const sw = file("sw.js").toString("utf8");
assert.ok(!sw.includes("__PWA_ASSETS__"));
assert.ok(!sw.includes("__PWA_CACHE_VERSION__"));
assert.match(sw, /data\/vehicles\.json/);
assert.match(sw, /request\.headers\.has\("Range"\)/);
assert.match(sw, /\.pmtiles/);
assert.match(sw, /"assets\//);
assert.ok(readdirSync(new URL("../dist/assets/", import.meta.url)).length > 0);
console.log("PWA validado: manifesto, ícones, chunks, escopo e isolamento do GPS/PMTiles.");
