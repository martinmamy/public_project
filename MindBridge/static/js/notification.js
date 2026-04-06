document.addEventListener("DOMContentLoaded", () => {

  const list = document.getElementById("notificationList");
  const count = document.getElementById("notifCount");
  const markAllBtn = document.getElementById("markAllRead");

  if (!list || !count || !markAllBtn) return;

  let currentPage = 1;
  const pageSize = 10;
  let notificationsCache = [];

  // =========================
  // PREVENT DROPDOWN CLOSE
  // =========================
  list.addEventListener("click", (e) => {
    e.stopPropagation();
  });

  // =========================
  // CSRF HELPER
  // =========================
  const getCSRF = () => {
    return (
      document.querySelector('meta[name="csrf-token"]')?.content ||
      document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
      document.cookie.split("; ").find(c => c.startsWith("csrftoken="))?.split("=")[1] ||
      ""
    );
  };

  // =========================
  // RENDER NOTIFICATIONS
  // =========================
  const renderNotifications = (append = false) => {

    if (!append) {
      list.innerHTML = "";
    }

    const start = (currentPage - 1) * pageSize;
    const paginated = notificationsCache.slice(start, start + pageSize);

    paginated.forEach(n => {

      const item = document.createElement("div");
      item.className = "dropdown-item d-flex justify-content-between align-items-start py-2";
      item.dataset.id = n.id;

      // Avatar
      let avatarHTML = "";
      if (n.actor?.avatar_url) {
        avatarHTML = `
          <img src="${n.actor.avatar_url}"
               class="rounded-circle me-2"
               style="width:32px;height:32px;object-fit:cover;">
        `;
      } else if (n.actor?.username) {
        avatarHTML = `
          <div class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center me-2"
               style="width:32px;height:32px;font-weight:bold;">
            ${n.actor.username.charAt(0).toUpperCase()}
          </div>
        `;
      }

      item.innerHTML = `
        <div class="d-flex flex-grow-1">
          ${avatarHTML}

          <input type="checkbox" class="form-check-input me-2 mark-read"
            ${n.is_read ? "checked" : ""}>

          <div>
            <a href="${n.url || "#"}"
               class="notif-link d-block ${n.is_read ? "" : "fw-bold"}">
              ${n.message}
            </a>
            <small class="text">${n.created_at}</small>
          </div>
        </div>

        <button class="btn btn-sm btn-link text-danger delete-notif p-0 ms-2">
          &times;
        </button>
      `;

      list.appendChild(item);
    });

    // =========================
    // LOAD MORE BUTTON
    // =========================
    let loadMoreBtn = document.getElementById("loadMoreNotif");

    if (!loadMoreBtn) {
      loadMoreBtn = document.createElement("div");
      loadMoreBtn.id = "loadMoreNotif";
      loadMoreBtn.className = "dropdown-item text-center text-primary";
      loadMoreBtn.style.cursor = "pointer";
      loadMoreBtn.textContent = "Load more...";
      list.appendChild(loadMoreBtn);
    }

    loadMoreBtn.style.display =
      notificationsCache.length <= currentPage * pageSize ? "none" : "block";

    // =========================
    // UNREAD COUNT
    // =========================
    const unread = notificationsCache.filter(n => !n.is_read).length;
    count.textContent = unread || "";
  };

  // =========================
  // FETCH
  // =========================
  const loadNotifications = async () => {
    try {
      const res = await fetch("/notifications/");
      if (!res.ok) throw new Error();

      const data = await res.json();

      notificationsCache = data.notifications || [];
      currentPage = 1;

      renderNotifications(false);

    } catch {
      list.innerHTML = `<div class="dropdown-item text-muted text-center">Failed to load</div>`;
    }
  };

  // =========================
  // MARK READ
  // =========================
  const markRead = async (id) => {
    if (!id) return;
    try {
      await fetch(`/notifications/mark_read/${id}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRF() }
      });
    } catch {}
  };

  // =========================
  // DELETE
  // =========================
  const deleteNotif = async (id) => {
    if (!id) return false;

    try {
      const res = await fetch(`/notifications/delete/${id}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRF() }
      });

      const data = await res.json();
      return data.success;

    } catch {
      return false;
    }
  };

  // =========================
  // CLICK HANDLER
  // =========================
  list.addEventListener("click", async (e) => {

    // DELETE
    const del = e.target.closest(".delete-notif");
    if (del) {
      const item = del.closest(".dropdown-item");
      const id = item?.dataset.id;

      if (!id) return;

      const ok = await deleteNotif(id);

      if (ok) {
        notificationsCache = notificationsCache.filter(n => n.id != id);
        item.remove();
        renderNotifications(false);
      }
      return;
    }

    // MARK READ (link click)
    const link = e.target.closest(".notif-link");
    if (link) {
      const item = link.closest(".dropdown-item");
      await markRead(item?.dataset.id);
      return;
    }

    // LOAD MORE
    if (e.target.id === "loadMoreNotif") {
      e.preventDefault();

      currentPage++;

      const prevHeight = list.scrollHeight;

      renderNotifications(true);

      requestAnimationFrame(() => {
        list.scrollTo({
          top: prevHeight,
          behavior: "smooth"
        });
      });
    }
  });

  // =========================
  // CHECKBOX
  // =========================
  list.addEventListener("change", async (e) => {
    if (!e.target.classList.contains("mark-read")) return;

    const item = e.target.closest(".dropdown-item");
    await markRead(item?.dataset.id);

    loadNotifications();
  });

  // =========================
  // MARK ALL
  // =========================
  markAllBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    try {
      await fetch("/notifications/mark_all_read/", {
        method: "POST",
        headers: { "X-CSRFToken": getCSRF() }
      });

      loadNotifications();

    } catch {}
  });

  // =========================
  // INIT
  // =========================
  loadNotifications();
  setInterval(loadNotifications, 10000);

});