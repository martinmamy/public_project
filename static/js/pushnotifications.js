document.addEventListener("DOMContentLoaded", async () => {

  /* =========================================================
     CSRF
  ========================================================= */

  function getCSRF() {

    return (
      document.querySelector(
        '[name=csrfmiddlewaretoken]'
      )?.value ||

      document.cookie
        .split("; ")
        .find(c => c.startsWith("csrftoken="))
        ?.split("=")[1] ||

      ""
    );
  }

  /* =========================================================
     BASE64 HELPER
  ========================================================= */

  function urlBase64ToUint8Array(base64String) {

    const padding =
      "=".repeat(
        (4 - base64String.length % 4) % 4
      );

    const base64 =
      (base64String + padding)
        .replace(/-/g, "+")
        .replace(/_/g, "/");

    const rawData =
      atob(base64);

    return Uint8Array.from(
      [...rawData].map(
        char => char.charCodeAt(0)
      )
    );
  }

  /* =========================================================
     DEVICE PUSH NOTIFICATIONS ONLY
  ========================================================= */

  async function initializePushNotifications() {

    // =========================================
    // CHECK SUPPORT
    // =========================================
    if (!("serviceWorker" in navigator)) {

      console.warn(
        "❌ Service Worker unsupported"
      );

      return;
    }

    if (!("PushManager" in window)) {

      console.warn(
        "❌ PushManager unsupported"
      );

      return;
    }

    try {

      // =========================================
      // REGISTER SERVICE WORKER
      // =========================================
      const registration =
        await navigator.serviceWorker.register(
          "/static/pwa/service-worker.js"
        );

      console.log(
        "✅ Service Worker Registered"
      );

      // =========================================
      // REQUEST PERMISSION
      // =========================================
      const permission =
        await Notification.requestPermission();

      if (permission !== "granted") {

        console.warn(
          "❌ Notification permission denied"
        );

        return;
      }

      console.log(
        "✅ Notification permission granted"
      );

      // =========================================
      // GET EXISTING SUBSCRIPTION
      // =========================================
      let subscription =
        await registration.pushManager.getSubscription();

      // =========================================
      // CREATE NEW SUBSCRIPTION
      // =========================================
      if (!subscription) {

        subscription =
          await registration.pushManager.subscribe({

            userVisibleOnly: true,

            applicationServerKey:
              urlBase64ToUint8Array(
                window.VAPID_PUBLIC_KEY
              )
          });

        console.log(
          "✅ Push Subscription Created"
        );
      }

      // =========================================
      // SAVE SUBSCRIPTION TO BACKEND
      // =========================================
      await fetch("/push/save/", {

        method: "POST",

        headers: {

          "Content-Type":
            "application/json",

          "X-CSRFToken":
            getCSRF()
        },

        body:
          JSON.stringify(subscription)
      });

      console.log(
        "✅ Push Subscription Saved"
      );

    } catch (err) {

      console.error(
        "❌ Push Notification Init Error:",
        err
      );
    }
  }

  /* =========================================================
     INIT
  ========================================================= */

  await initializePushNotifications();

});