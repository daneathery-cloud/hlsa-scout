const CACHE = "hlsascout-20261031-123409";
function bust(url) { return url + (url.indexOf("?") === -1 ? "?" : "&") + "_sw=" + Date.now(); }
const SHELL = ["./", "./index.html", "./wire.html", "./orgs.html", "./watchlist.html", "./about.html",
  "./diagnostics.html", "./manifest.webmanifest", "./free.json", "./logo.png",
  "./icons/icon-192.png", "./icons/icon-512.png", "./icons/apple-touch-icon.png", "./icons/favicon-32.png"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  // This github.io address is shared with other apps (HLSA, TrendScout): only clear our own old caches.
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("hlsascout-") && k !== CACHE)
    .map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.endsWith("version.json")) { e.respondWith(fetch(bust(req.url), { cache: "no-store" })); return; }
  const fresh = req.mode === "navigate" || /\.(html|json|webmanifest)$/.test(url.pathname);
  if (fresh) {
    const key = req.url.split("#")[0].split("?")[0];
    e.respondWith(fetch(bust(req.url), { cache: "no-store" }).then((r) => {
        if (r.ok) { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(key, copy)); }
        return r;
      }).catch(() => caches.match(key).then((hit) => hit || caches.match("./index.html"))));
    return;
  }
  e.respondWith(caches.match(req).then((cached) => {
    const net = fetch(req).then((r) => { if (r.ok) { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); } return r; })
      .catch(() => cached);
    return cached || net;
  }));
});
