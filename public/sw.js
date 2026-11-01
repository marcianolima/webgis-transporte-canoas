/* Service worker no escopo do projeto GitHub Pages. Dados de GPS/API nunca são armazenados. */
const CACHE_VERSION = /*__PWA_CACHE_VERSION__*/ "dev";
const SHELL = "transporte-shell-" + CACHE_VERSION;
const REFERENCES = "transporte-reference-" + CACHE_VERSION;
const BASE = new URL(self.registration.scope);
const PRECACHE_ASSETS = /*__PWA_ASSETS__*/ [];
const SHELL_FILES = [
  "", "index.html", "favicon.svg", "manifest.webmanifest",
  "icons/icon-192.png", "icons/icon-512.png", ...PRECACHE_ASSETS
];
const localUrl = (path) => new URL(path, BASE).toString();

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL).then((cache) => cache.addAll(SHELL_FILES.map(localUrl)))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) =>
      key.startsWith("transporte-shell-") || key.startsWith("transporte-reference-")
    ).filter((key) => key !== SHELL && key !== REFERENCES).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
});

async function networkFirst(request, cacheName, fallback) {
  try {
    const response = await fetch(request);
    if (response.ok && response.type !== "opaque" &&
        !/no-store/i.test(response.headers.get("Cache-Control") || "")) {
      const cache = await caches.open(cacheName);
      await cache.put(request, response.clone());
    }
    return response;
  } catch {
    const old = await caches.match(request);
    if (old) return old;
    if (fallback) return (await caches.match(fallback)) || Response.error();
    return Response.error();
  }
}
async function cacheFirst(request) {
  const hit = await caches.match(request);
  if (hit) return hit;
  const response = await fetch(request);
  if (response.ok && response.type !== "opaque") {
    const cache = await caches.open(SHELL);
    await cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || request.headers.has("Range")) return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE.pathname)) return;
  const path = url.pathname.slice(BASE.pathname.length);
  // Nem arquivos PMTiles (range), nem posições de veículos, nem endpoints em tempo real.
  if (path.endsWith(".pmtiles") || path === "data/vehicles.json" ||
      path.includes("/v1/") || /vehicles|gps|position|eta/i.test(path)) return;
  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, SHELL, localUrl("index.html")));
    return;
  }
  if (/^data\/[\w.-]+\.(json|geojson)$/.test(path)) {
    event.respondWith(networkFirst(request, REFERENCES));
    return;
  }
  if (path.startsWith("assets/") || SHELL_FILES.includes(path)) {
    event.respondWith(cacheFirst(request));
  }
});
