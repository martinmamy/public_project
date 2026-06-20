document.addEventListener("DOMContentLoaded", () => {

  /* =========================================================
     ELEMENTS
  ========================================================= */

  const container =
    document.getElementById("notificationItems");

  const count =
    document.getElementById("notifCount");

  const markAllBtn =
    document.getElementById("markAllRead");

  const notifList =
    document.getElementById("notificationList");

  if (
    !container ||
    !count ||
    !markAllBtn
  ) {
    return;
  }

  /* =========================================================
     STATE
  ========================================================= */

  let notificationsCache = [];

  let currentPage = 1;

  const pageSize = 10;

  let loadingNotifications = false;

  /* =========================================================
     PREVENT DROPDOWN CLOSE
  ========================================================= */

  notifList?.addEventListener(
    "click",
    (e) => {
      e.stopPropagation();
    }
  );

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
        .find(c =>
          c.startsWith("csrftoken=")
        )
        ?.split("=")[1] ||

      ""
    );
  }

  /* =========================================================
     UPDATE COUNT
  ========================================================= */

  function updateCount() {

    const unread =
      notificationsCache.filter(
        n => !n.is_read
      ).length;

    count.textContent =
      unread > 0
        ? unread
        : "";
  }

  /* =========================================================
     LOAD MORE
  ========================================================= */

  function renderLoadMore() {

    let btn =
      document.getElementById(
        "loadMoreNotif"
      );

    if (
      notificationsCache.length >
      currentPage * pageSize
    ) {

      if (!btn) {

        btn =
          document.createElement("div");

        btn.id =
          "loadMoreNotif";

        btn.className =
          "text-center text-primary py-2";

        btn.style.cursor =
          "pointer";

        btn.textContent =
          "Load more...";

        container.appendChild(btn);
      }

    } else {

      btn?.remove();
    }
  }

  /* =========================================================
     RENDER
  ========================================================= */

  function renderNotifications() {

    container.innerHTML = "";

    const items =
      notificationsCache.slice(
        0,
        currentPage * pageSize
      );

    if (!items.length) {

      container.innerHTML = `
        <div class="text-center p-3">
          No notifications
        </div>
      `;

      return;
    }

    items.forEach((n) => {

      const item =
        document.createElement("div");

      item.className =
        "dropdown-item d-flex justify-content-between align-items-start py-2";

      item.dataset.id = n.id;

      let avatar = "";

      if (n.actor?.avatar_url) {

        avatar = `
          <img
            src="${n.actor.avatar_url}"
            class="rounded-circle me-2"
            style="width:32px;height:32px;object-fit:cover;"
          >
        `;

      } else if (n.actor?.username) {

        avatar = `
          <div
            class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center me-2"
            style="width:32px;height:32px;font-weight:bold;"
          >
            ${n.actor.username
              .charAt(0)
              .toUpperCase()}
          </div>
        `;
      }

      item.innerHTML = `
        <div class="d-flex flex-grow-1">

          ${avatar}

          <input
            type="checkbox"
            class="form-check-input me-2 mark-read"
            ${n.is_read ? "checked" : ""}
          >

          <div>

            <a
              href="${n.url || "#"}"
              class="notif-link d-block ${n.is_read ? "" : "fw-bold"}"
            >
              ${n.message}
            </a>

            <small>
              ${n.created_at}
            </small>

          </div>

        </div>

        <button
          class="btn btn-sm btn-link text-danger delete-notif p-0 ms-2"
        >
          &times;
        </button>
      `;

      container.appendChild(item);
    });

    renderLoadMore();

    updateCount();
  }

  /* =========================================================
     FETCH NOTIFICATIONS
  ========================================================= */

  async function loadNotifications(
    resetPage = true
  ) {

    if (loadingNotifications) {
      return;
    }

    loadingNotifications = true;

    try {

      const res =
        await fetch(
          "/notifications/"
        );

      const data =
        await res.json();

      notificationsCache =
        data.notifications || [];

      if (resetPage) {
        currentPage = 1;
      }

      renderNotifications();

    } catch (err) {

      console.error(err);

      container.innerHTML = `
        <div class="text-center text-danger p-3">
          Failed to load notifications
        </div>
      `;

    } finally {

      loadingNotifications = false;
    }
  }

  /* =========================================================
     ACTIONS
  ========================================================= */

  async function markRead(id) {

    if (!id) return;

    try {

      await fetch(
        `/notifications/mark_read/${id}/`,
        {

          method: "POST",

          headers: {
            "X-CSRFToken":
              getCSRF()
          }
        }
      );

    } catch (err) {

      console.error(err);
    }
  }

  async function deleteNotif(id) {

    try {

      const res =
        await fetch(
          `/notifications/delete/${id}/`,
          {

            method: "POST",

            headers: {
              "X-CSRFToken":
                getCSRF()
            }
          }
        );

      const data =
        await res.json();

      return data.success;

    } catch (err) {

      console.error(err);

      return false;
    }
  }

  async function markAllRead() {

    try {

      await fetch(
        "/notifications/mark_all_read/",
        {

          method: "POST",

          headers: {
            "X-CSRFToken":
              getCSRF()
          }
        }
      );

    } catch (err) {

      console.error(err);
    }
  }

  /* =========================================================
     CLICK EVENTS
  ========================================================= */

  container.addEventListener(
    "click",
    async (e) => {

      /* DELETE */
      if (
        e.target.closest(
          ".delete-notif"
        )
      ) {

        const item =
          e.target.closest(
            ".dropdown-item"
          );

        const id =
          item.dataset.id;

        const ok =
          await deleteNotif(id);

        if (ok) {

          notificationsCache =
            notificationsCache.filter(
              n => n.id != id
            );

          renderNotifications();
        }

        return;
      }

      /* MARK READ */
      if (
        e.target.closest(
          ".notif-link"
        )
      ) {

        const item =
          e.target.closest(
            ".dropdown-item"
          );

        const id =
          item.dataset.id;

        await markRead(id);

        notificationsCache =
          notificationsCache.map(n => {

            if (n.id == id) {
              n.is_read = true;
            }

            return n;
          });

        renderNotifications();

        return;
      }

      /* LOAD MORE */
      if (
        e.target.id ===
        "loadMoreNotif"
      ) {

        currentPage++;

        renderNotifications();
      }
    }
  );

  /* =========================================================
     CHECKBOX
  ========================================================= */

  container.addEventListener(
    "change",
    async (e) => {

      if (
        !e.target.classList.contains(
          "mark-read"
        )
      ) {
        return;
      }

      const item =
        e.target.closest(
          ".dropdown-item"
        );

      const id =
        item.dataset.id;

      await markRead(id);

      notificationsCache =
        notificationsCache.map(n => {

          if (n.id == id) {
            n.is_read = true;
          }

          return n;
        });

      updateCount();
    }
  );

  /* =========================================================
     MARK ALL
  ========================================================= */

  markAllBtn.addEventListener(
    "click",
    async () => {

      await markAllRead();

      notificationsCache =
        notificationsCache.map(n => {

          n.is_read = true;

          return n;
        });

      renderNotifications();
    }
  );

  /* =========================================================
     LIVE PUSH REFRESH
  ========================================================= */

  if ("serviceWorker" in navigator) {

    navigator.serviceWorker.addEventListener(
      "message",
      (event) => {

        if (
          event.data &&
          event.data.type === "NEW_NOTIFICATION"
        ) {

          console.log(
            "🔔 New notification received"
          );

          loadNotifications(false);
        }
      }
    );
  }

  /* =========================================================
     AUTO REFRESH FALLBACK
  ========================================================= */

  loadNotifications();

  setInterval(
    () => loadNotifications(false),
    5000
  );

});