const CACHE_NAME = "mindbridge-v5";

/* =========================
   CACHE FILES
========================= */
const urlsToCache = [
  "/",
  "/manifest.json",
  "/favicon.ico",

  "/static/css/bootstrap.min.css",
  "/static/css/main.css",

  "/static/js/main.js",
  "/static/js/notification.js",
  "/static/js/push.js",

  "/static/images/default-avatar.png"
];

/* =========================
   INSTALL
========================= */
self.addEventListener("install", (event) => {

  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
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

      if (cached) {
        return cached;
      }

      return fetch(event.request)
        .then((response) => {

          if (
            !response ||
            response.status !== 200 ||
            response.type !== "basic"
          ) {
            return response;
          }

          const clone = response.clone();

          caches.open(CACHE_NAME)
            .then((cache) => cache.put(event.request, clone));

          return response;
        })
        .catch(() => caches.match("/"));
    })
  );
});

/* =========================
   PUSH EVENT
========================= */
self.addEventListener("push", (event) => {

  let data = {};

  try {
    data = event.data.json();
  } catch (err) {
    data = {
      title: "MindBridge",
      body: "You received a notification",
      url: "/"
    };
  }

  const options = {
    body: data.body || "",
    icon: data.icon || "/static/images/default-avatar.png",
    badge: "/static/images/default-avatar.png",

    image: data.image || null,

    vibrate: [200, 100, 200],

    requireInteraction: true,

    tag: data.tag || "general",

    renotify: true,

    data: {
      url: data.url || "/"
    },

    actions: [
      {
        action: "open",
        title: "Open"
      },
      {
        action: "close",
        title: "Dismiss"
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(
      data.title || "MindBridge",
      options
    )
  );
});

/* =========================
   NOTIFICATION CLICK
========================= */
self.addEventListener("notificationclick", (event) => {

  event.notification.close();

  if (event.action === "close") {
    return;
  }

  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(

    clients.matchAll({
      type: "window",
      includeUncontrolled: true
    }).then((clientsArr) => {

      for (const client of clientsArr) {

        if (client.url.includes(targetUrl) && "focus" in client) {
          return client.focus();
        }
      }

      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});