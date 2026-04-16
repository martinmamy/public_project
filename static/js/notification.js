document.addEventListener("DOMContentLoaded", () => {

  const container = document.getElementById("notificationItems");
  const count = document.getElementById("notifCount");
  const markAllBtn = document.getElementById("markAllRead");

  if (!container || !count || !markAllBtn) return;

  let notificationsCache = [];
  let currentPage = 1;
  const pageSize = 10;

  // =========================
  // PREVENT CLOSE
  // =========================
  document.getElementById("notificationList").addEventListener("click", (e) => {
    e.stopPropagation();
  });

  // =========================
  // CSRF
  // =========================
  const getCSRF = () =>
    document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
    document.cookie.split("; ").find(c => c.startsWith("csrftoken="))?.split("=")[1] ||
    "";

  // =========================
  // RENDER
  // =========================
  const renderNotifications = (append = false) => {

    if (!append) {
      container.innerHTML = "";
    }

    const start = (currentPage - 1) * pageSize;
    const items = notificationsCache.slice(start, start + pageSize);

    if (!items.length && !append) {
      container.innerHTML = `<div class="text-center p-3">No notifications</div>`;
      return;
    }

    items.forEach(n => {

      const item = document.createElement("div");
      item.className = "dropdown-item d-flex justify-content-between align-items-start py-2";
      item.dataset.id = n.id;

      let avatar = "";

      if (n.actor?.avatar_url) {
        avatar = `<img src="${n.actor.avatar_url}" class="rounded-circle me-2"
                    style="width:32px;height:32px;object-fit:cover;">`;
      } else if (n.actor?.username) {
        avatar = `<div class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center me-2"
                    style="width:32px;height:32px;font-weight:bold;">
                    ${n.actor.username.charAt(0).toUpperCase()}
                  </div>`;
      }

      item.innerHTML = `
        <div class="d-flex flex-grow-1">
          ${avatar}

          <input type="checkbox" class="form-check-input me-2 mark-read"
            ${n.is_read ? "checked" : ""}>

          <div>
            <a href="${n.url || "#"}"
               class="notif-link d-block ${n.is_read ? "" : "fw-bold"}">
              ${n.message}
            </a>
            <small>${n.created_at}</small>
          </div>
        </div>

        <button class="btn btn-sm btn-link text-danger delete-notif p-0 ms-2">
          &times;
        </button>
      `;

      container.appendChild(item);
    });

    renderLoadMore();
    updateCount();
  };

  // =========================
  // LOAD MORE BUTTON
  // =========================
  const renderLoadMore = () => {

    let btn = document.getElementById("loadMoreNotif");

    if (notificationsCache.length > currentPage * pageSize) {

      if (!btn) {
        btn = document.createElement("div");
        btn.id = "loadMoreNotif";
        btn.className = "text-center text-primary py-2";
        btn.style.cursor = "pointer";
        btn.textContent = "Load more...";
        container.appendChild(btn);
      }

    } else {
      btn?.remove();
    }
  };

  // =========================
  // COUNT
  // =========================
  const updateCount = () => {
    const unread = notificationsCache.filter(n => !n.is_read).length;
    count.textContent = unread || "";
  };

  // =========================
  // FETCH
  // =========================
  const loadNotifications = async () => {
    try {
      const res = await fetch("/notifications/");
      const data = await res.json();

      notificationsCache = data.notifications || [];
      currentPage = 1;

      renderNotifications(false);

    } catch {
      container.innerHTML = `<div class="text-center text-danger p-3">Failed to load</div>`;
    }
  };

  // =========================
  // ACTIONS
  // =========================
  const markRead = async (id) => {
    if (!id) return;
    await fetch(`/notifications/mark_read/${id}/`, {
      method: "POST",
      headers: { "X-CSRFToken": getCSRF() }
    });
  };

  const deleteNotif = async (id) => {
    const res = await fetch(`/notifications/delete/${id}/`, {
      method: "POST",
      headers: { "X-CSRFToken": getCSRF() }
    });

    const data = await res.json();
    return data.success;
  };

  const markAllRead = async () => {
    await fetch("/notifications/mark_all_read/", {
      method: "POST",
      headers: { "X-CSRFToken": getCSRF() }
    });
  };

  // =========================
  // CLICK EVENTS
  // =========================
  container.addEventListener("click", async (e) => {

    // DELETE
    if (e.target.closest(".delete-notif")) {
      const item = e.target.closest(".dropdown-item");
      const id = item.dataset.id;

      const ok = await deleteNotif(id);

      if (ok) {
        notificationsCache = notificationsCache.filter(n => n.id != id);
        item.remove();
        updateCount();
      }
      return;
    }

    // LINK CLICK
    if (e.target.closest(".notif-link")) {
      const item = e.target.closest(".dropdown-item");
      await markRead(item.dataset.id);
      return;
    }

    // LOAD MORE
    if (e.target.id === "loadMoreNotif") {
      currentPage++;
      renderNotifications(true);
    }
  });

  // =========================
  // CHECKBOX
  // =========================
  container.addEventListener("change", async (e) => {
    if (!e.target.classList.contains("mark-read")) return;

    const item = e.target.closest(".dropdown-item");
    await markRead(item.dataset.id);

    loadNotifications();
  });

  // =========================
  // MARK ALL BUTTON
  // =========================
  markAllBtn.addEventListener("click", async () => {
    await markAllRead();
    loadNotifications();
  });

  // =========================
  // INIT
  // =========================
  loadNotifications();
  setInterval(loadNotifications, 10000);

});