const CACHE_NAME = "fancylearn-v3";

const urlsToCache = [
  "/",
  "/manifest.json",
  "/favicon.ico",

  "/static/css/bootstrap.min.css",
  "/static/css/main.css",
  "/static/css/list_problem.css",
  "/static/css/problem_detail.css",
  "/static/css/talenthub.css",

  "/static/js/main.js",
  "/static/js/notification.js",
  "/static/js/theme.js",
  "/static/js/tips.js",

  "/static/sounds/notification.mp3",
  "/static/images/default-avatar.png"
];

/* =========================
   INSTALL
========================= */
self.addEventListener("install", (event) => {
  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
  );
});

/* =========================
   ACTIVATE
========================= */
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );

  self.clients.claim();
});

/* =========================
   FETCH
========================= */
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;

      return fetch(event.request).then((res) => {
        if (!res || res.status !== 200 || res.type !== "basic") {
          return res;
        }

        const clone = res.clone();

        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, clone);
        });

        return res;
      });
    })
  );
});

/* =========================
   NOTIFICATION CLICK FIX
========================= */
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification.data?.url || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientsArr) => {
      for (const client of clientsArr) {
        if ("focus" in client) {
          client.focus();
          client.navigate(url);
          return;
        }
      }

      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

/* =========================
   PUSH EVENT (MISSING PIECE)
========================= */
self.addEventListener("push", function (event) {

  let data = {};

  try {
    data = event.data.json();
  } catch (e) {
    data = {
      title: "Notification",
      body: "You have a new update",
      url: "/"
    };
  }

  event.waitUntil(
    self.registration.showNotification(data.title || "Notification", {
      body: data.body || "",
      icon: data.icon || "/static/images/default-avatar.png",
      badge: "/static/images/default-avatar.png",
      data: {
        url: data.url || "/"
      },
      tag: data.tag || "general",
      renotify: true
    })
  );
});