// Service worker : l'interface et le guide restent consultables sans réseau sur le chantier.
// Les données (API) ne sont jamais mises en cache : elles restent sur le serveur.
const CACHE = "mmt-v1";
const COQUILLE = ["/", "/manifest.webmanifest", "/icone-192.png", "/icone-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(COQUILLE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((cles) => Promise.all(cles.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  if (url.pathname.startsWith("/assets/")) {
    // fichiers versionnés : cache d'abord
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request).then((rep) => {
      const copie = rep.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copie));
      return rep;
    })));
    return;
  }
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).then((rep) => {
      const copie = rep.clone();
      caches.open(CACHE).then((c) => c.put("/", copie));
      return rep;
    }).catch(() => caches.match("/")));
  }
});
