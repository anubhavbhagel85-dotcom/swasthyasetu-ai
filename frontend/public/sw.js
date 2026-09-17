// Minimal service worker for SwasthyaSetu AI.
// Goal: once a user has opened the app once, the app SHELL (HTML/CSS/JS)
// keeps loading even with zero connectivity, so the on-device offline
// engine (src/offline/offlineEngine.js) has something to run inside.
// This deliberately does NOT cache API calls to the backend — those should
// always try the network first and let App.jsx's own fallback logic decide
// what to do if they fail.

const CACHE_NAME = "swasthyasetu-shell-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  // Never intercept cross-origin calls (i.e. the backend API) — let the
  // app's own online/offline fallback logic handle those.
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(request);
      const networkFetch = fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            cache.put(request, response.clone());
          }
          return response;
        })
        .catch(() => cached || caches.match("/index.html"));

      // Stale-while-revalidate: serve cached instantly if we have it,
      // refresh the cache in the background either way.
      return cached || networkFetch;
    })
  );
});
