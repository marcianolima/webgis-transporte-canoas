/* Embute os chunks versionados de Vite no precache e invalida o SW em cada build. */
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
const root = new URL("../dist/", import.meta.url);
const dir = new URL("../dist/assets/", import.meta.url);
const assets = [];
function collect(directory) {
  for (const file of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, file.name);
    if (file.isDirectory()) collect(path);
    else if (/\.(js|css)$/.test(file.name)) assets.push(relative(new URL(".", root).pathname, path).replaceAll("\\", "/"));
  }
}
collect(dir.pathname);
assets.sort();
const swPath = new URL("../dist/sw.js", import.meta.url);
let source = readFileSync(swPath, "utf8");
const version = createHash("sha256").update(assets.join("\n") + source).digest("hex").slice(0, 16);
if (!source.includes("/*__PWA_ASSETS__*/ []") || !source.includes('/*__PWA_CACHE_VERSION__*/ "dev"'))
  throw Error("Marcadores de precache não encontrados.");
source = source.replace("/*__PWA_ASSETS__*/ []", JSON.stringify(assets))
  .replace('/*__PWA_CACHE_VERSION__*/ "dev"', JSON.stringify(version));
writeFileSync(swPath, source);
