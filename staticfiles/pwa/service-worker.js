const CACHE_NAME = "fancylearn-v1";
const urlsToCache = [
  "/",
  "/static/css/bootstrap.min.css",
  "/static/js/main.js",
  "/static/js/notification.js",
  "/static/js/theme.js",
  "/static/js/tips.js",
  "/static/css/list_problem.css",
  "/static/css/problem_detail.css",
  "/static/css/main.css",
  "/static/css/talenthub.css",
];

// Install
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Activate
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
});

// Fetch (offline support)
self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});