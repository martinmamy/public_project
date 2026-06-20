// =========================================================
// CACHE CONFIG
// =========================================================
const CACHE_NAME = "mindbridge-v1.0.0";

const urlsToCache = [

  "/",
  "/favicon.ico",

  "/static/css/main.css",

  "/static/js/main.js",
  "/static/js/notification.js",
  "/static/js/pushnotifications.js",

  "/static/pwa/manifest.json",
  "/static/pwa/service-worker.js",

  "/static/logo/favicon-16.png",
  "/static/logo/favicon-32.png",
  "/static/logo/favicon-256.png",
  "/static/logo/favicon.ico",
  "/static/logo/favicon.png",

  "/static/pwa/icons/icon-16.png",
  "/static/pwa/icons/icon-32.png",
  "/static/pwa/icons/icon-192.png",
  "/static/pwa/icons/icon-256.png",
  "/static/pwa/icons/icon-512.png",

  "/static/sounds/notification.mp3",

];


// =========================================================
// INSTALL
// =========================================================
self.addEventListener("install", (event) => {

  self.skipWaiting();

  event.waitUntil(

    (async () => {

      const cache = await caches.open(CACHE_NAME);

      for (const url of urlsToCache) {

        try {

          const response = await fetch(url, {
            cache: "no-cache"
          });

          // ===============================
          // ONLY CACHE VALID RESPONSES
          // ===============================
          if (!response.ok) {

            console.warn(
              "[SW] Failed to cache:",
              url,
              response.status
            );

            continue;
          }

          await cache.put(url, response);

          console.log(
            "[SW] Cached:",
            url
          );

        } catch (error) {

          console.error(
            "[SW] Cache error:",
            url,
            error
          );
        }
      }

    })()
  );
});


// =========================================================
// ACTIVATE
// =========================================================
self.addEventListener("activate", (event) => {

  event.waitUntil(

    (async () => {

      const keys = await caches.keys();

      await Promise.all(

        keys.map((key) => {

          if (key !== CACHE_NAME) {

            console.log(
              "[SW] Removing old cache:",
              key
            );

            return caches.delete(key);
          }
        })
      );

      await self.clients.claim();

    })()
  );
});


// =========================================================
// FETCH
// =========================================================
self.addEventListener("fetch", (event) => {

  if (event.request.method !== "GET") {
    return;
  }

  event.respondWith(

    (async () => {

      try {

        // ===============================
        // CACHE FIRST
        // ===============================
        const cachedResponse =
          await caches.match(event.request);

        if (cachedResponse) {
          return cachedResponse;
        }

        // ===============================
        // NETWORK REQUEST
        // ===============================
        const networkResponse =
          await fetch(event.request);

        // ===============================
        // VALIDATE RESPONSE
        // ===============================
        if (
          networkResponse &&
          networkResponse.status === 200 &&
          (
            networkResponse.type === "basic" ||
            networkResponse.type === "cors"
          )
        ) {

          const responseClone =
            networkResponse.clone();

          const cache =
            await caches.open(CACHE_NAME);

          cache.put(
            event.request,
            responseClone
          );
        }

        return networkResponse;

      } catch (error) {

        console.error(
          "[SW] Fetch failed:",
          error
        );

        // ===============================
        // OFFLINE FALLBACK
        // ===============================
        const fallback =
          await caches.match("/");

        return (
          fallback ||
          new Response(
            "Offline",
            {
              status: 503,
              statusText: "Offline"
            }
          )
        );
      }

    })()
  );
});


// =========================================================
// PUSH EVENT
// =========================================================
self.addEventListener("push", (event) => {

  let data = {};

  try {

    data = event.data.json();

  } catch (err) {

    data = {

      title: "FancyLearn",

      body: "You received a notification",

      url: "/"
    };
  }

  const options = {

    body:
      data.body || "",

    icon:
      data.icon ||
      "/static/pwa/icons/icon-32.png",

    badge:
      "/static/pwa/icons/icon-32.png",

    image:
      data.image || null,

    vibrate: [200, 100, 200],

    requireInteraction: true,

    tag:
      data.tag || "general",

    renotify: true,

    data: {

      url:
        data.url || "/"
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

    (async () => {

      // ===============================
      // SHOW DEVICE NOTIFICATION
      // ===============================
      await self.registration.showNotification(

        data.title || "FancyLearn",

        options
      );

      // ===============================
      // SEND MESSAGE TO OPEN TABS
      // ===============================
      const clientsList =
        await clients.matchAll({

          type: "window",

          includeUncontrolled: true
        });

      for (const client of clientsList) {

        client.postMessage({

          type: "NEW_NOTIFICATION"
        });
      }

    })()
  );
});

// =========================================================
// NOTIFICATION CLICK
// =========================================================
self.addEventListener(

  "notificationclick",

  (event) => {

    event.notification.close();

    // ===============================
    // CLOSE ACTION
    // ===============================
    if (event.action === "close") {
      return;
    }

    const targetUrl =
      event.notification.data?.url || "/";

    event.waitUntil(

      (async () => {

        const clientList =
          await clients.matchAll({

            type: "window",

            includeUncontrolled: true
          });

        // ===========================
        // FOCUS EXISTING TAB
        // ===========================
        for (const client of clientList) {

          if (
            client.url.includes(targetUrl) &&
            "focus" in client
          ) {

            return client.focus();
          }
        }

        // ===========================
        // OPEN NEW TAB
        // ===========================
        if (clients.openWindow) {

          return clients.openWindow(
            targetUrl
          );
        }

      })()
    );
  }
);