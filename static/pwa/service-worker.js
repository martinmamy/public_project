const CACHE_NAME = "fancylearn-v2"; // Increment version when updating
const urlsToCache = [
  "/", 
  "/static/css/bootstrap.min.css",
  "/static/css/main.css",
  "/static/css/list_problem.css",
  "/static/css/problem_detail.css",
  "/static/css/talenthub.css",
  "/static/js/main.js",
  "/static/js/notification.js",
  "/static/js/theme.js",
  "/static/js/tips.js",
  "/favicon.ico",
  "/manifest.json"
];

// Install: cache essential assets
self.addEventListener("install", event => {
    self.skipWaiting(); // Activate SW immediately
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
});

// Activate: cleanup old caches
self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.map(key => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            )
        )
    );
    self.clients.claim(); // Take control immediately
});

// Fetch: cache-first strategy with network fallback
self.addEventListener("fetch", event => {
    // Ignore non-GET requests
    if (event.request.method !== "GET") return;

    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            if (cachedResponse) return cachedResponse;

            return fetch(event.request)
                .then(networkResponse => {
                    // Only cache valid responses
                    if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== "basic") {
                        return networkResponse;
                    }

                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
                    return networkResponse;
                })
                .catch(() => {
                    // Optional: fallback page or asset if offline
                    if (event.request.destination === "document") {
                        return caches.match("/");
                    }
                });
        })
    );
});