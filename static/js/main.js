/* ===========================================================================
   Restaurant Management System - Core JS
   Theme toggle, notifications, modals, toasts, confirm dialogs, helpers.
   =========================================================================== */
(function () {
    "use strict";

    // ---- Theme handling ----
    function applyTheme(mode) {
        if (mode === "dark") {
            document.documentElement.setAttribute("data-theme", "dark");
        } else {
            document.documentElement.removeAttribute("data-theme");
        }
    }
    // Initialize from saved preference or server default
    var saved = localStorage.getItem("theme");
    if (saved) {
        applyTheme(saved);
    } else {
        var serverMode = document.documentElement.getAttribute("data-theme-default");
        if (serverMode) applyTheme(serverMode);
    }

    document.addEventListener("click", function (e) {
        var toggle = e.target.closest("[data-theme-toggle]");
        if (toggle) {
            var isDark = document.documentElement.getAttribute("data-theme") === "dark";
            var next = isDark ? "light" : "dark";
            applyTheme(next);
            localStorage.setItem("theme", next);
            // Persist to server if endpoint provided
            var url = toggle.getAttribute("data-theme-save");
            if (url) {
                fetch(url, { method: "POST", headers: { "X-CSRFToken": getCsrf() } })
                    .catch(function () { });
            }
        }
    });

    // ---- Sidebar toggle (mobile) ----
    document.addEventListener("click", function (e) {
        var ham = e.target.closest("[data-sidebar-toggle]");
        if (ham) {
            var sb = document.querySelector(".sidebar");
            if (sb) sb.classList.toggle("open");
        }
        var overlay = e.target.closest("[data-sidebar-close]");
        if (overlay) {
            var s = document.querySelector(".sidebar");
            if (s) s.classList.remove("open");
        }
    });

    // ---- Mobile public nav ----
    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-nav-toggle]");
        if (btn) {
            var links = document.querySelector(".public-nav .links");
            if (links) links.classList.toggle("open");
        }
    });

    // ---- CSRF token from meta ----
    function getCsrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.getAttribute("content") : "";
    }

    // ---- Toasts ----
    function showToast(type, title, msg) {
        var container = document.querySelector(".toast-container");
        if (!container) {
            container = document.createElement("div");
            container.className = "toast-container";
            document.body.appendChild(container);
        }
        var t = document.createElement("div");
        t.className = "toast " + (type || "info");
        t.innerHTML =
            '<div class="t-title">' + (title || "") + "</div>" +
            '<div class="t-msg">' + (msg || "") + "</div>";
        container.appendChild(t);
        setTimeout(function () {
            t.style.opacity = "0";
            t.style.transition = "opacity .3s";
            setTimeout(function () { t.remove(); }, 300);
        }, 4000);
    }
    window.showToast = showToast;

    // ---- Flash messages from server (data attributes) ----
    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-flash]").forEach(function (el) {
            showToast(el.getAttribute("data-flash"), el.getAttribute("data-title"), el.getAttribute("data-msg"));
            el.remove();
        });
    });

    // ---- Confirm delete / action ----
    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-confirm]");
        if (btn) {
            var msg = btn.getAttribute("data-confirm") || "Are you sure?";
            if (!confirm(msg)) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        }
    });

    // ---- AJAX action buttons (data-action) ----
    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-action]");
        if (!btn) return;
        e.preventDefault();
        var url = btn.getAttribute("data-url");
        var method = btn.getAttribute("data-method") || "POST";
        var confirmMsg = btn.getAttribute("data-confirm");
        if (confirmMsg && !confirm(confirmMsg)) return;
        btn.disabled = true;
        fetch(url, {
            method: method,
            headers: { "X-CSRFToken": getCsrf(), "Content-Type": "application/json" },
            body: method === "POST" ? JSON.stringify({}) : null,
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                btn.disabled = false;
                if (data.ok) {
                    if (data.message) showToast("success", "Success", data.message);
                    if (btn.getAttribute("data-reload") !== "false") location.reload();
                } else {
                    showToast("danger", "Error", data.error || "Action failed.");
                }
            })
            .catch(function () {
                btn.disabled = false;
                showToast("danger", "Error", "Network error.");
            });
    });

    // ---- Generic form submit via fetch (data-ajax-form) ----
    document.addEventListener("submit", function (e) {
        var form = e.target.closest("form[data-ajax]");
        if (!form) return;
        e.preventDefault();
        var btn = form.querySelector("button[type=submit]");
        if (btn) btn.disabled = true;
        fetch(form.action, {
            method: form.method || "POST",
            headers: { "X-CSRFToken": getCsrf() },
            body: new FormData(form),
        })
            .then(function (r) { return r.json().catch(function () { return {}; }); })
            .then(function (data) {
                if (btn) btn.disabled = false;
                if (data.ok) {
                    if (data.message) showToast("success", "Success", data.message);
                    if (form.getAttribute("data-reload") !== "false") location.reload();
                } else if (data.error) {
                    showToast("danger", "Error", data.error);
                }
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                showToast("danger", "Error", "Network error.");
            });
    });

    // ---- Modal helpers ----
    window.openModal = function (id) {
        var m = document.getElementById(id);
        if (m) m.classList.add("open");
    };
    window.closeModal = function (id) {
        var m = document.getElementById(id);
        if (m) m.classList.remove("open");
    };
    document.addEventListener("click", function (e) {
        if (e.target.classList && e.target.classList.contains("modal-overlay")) {
            e.target.classList.remove("open");
        }
        var c = e.target.closest("[data-close-modal]");
        if (c) {
            var modal = c.closest(".modal-overlay");
            if (modal) modal.classList.remove("open");
        }
    });

    // ---- Notifications dropdown + polling ----
    var notifBell = document.querySelector("[data-notif-bell]");
    if (notifBell) {
        notifBell.addEventListener("click", function (e) {
            e.stopPropagation();
            var dd = document.querySelector(".notif-dropdown");
            if (dd) dd.classList.toggle("open");
        });
        document.addEventListener("click", function () {
            var dd = document.querySelector(".notif-dropdown");
            if (dd) dd.classList.remove("open");
        });
    }

    function loadNotifications() {
        fetch("/api/notifications")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var countEl = document.querySelector("[data-notif-count]");
                if (countEl) {
                    if (data.unread > 0) {
                        countEl.textContent = data.unread;
                        countEl.style.display = "inline-block";
                    } else {
                        countEl.style.display = "none";
                    }
                }
                var list = document.querySelector("[data-notif-list]");
                if (list) {
                    if (!data.items.length) {
                        list.innerHTML = '<div class="notif-item"><div class="n-msg">No notifications</div></div>';
                    } else {
                        list.innerHTML = data.items.map(function (n) {
                            return '<a class="notif-item ' + (n.is_read ? "" : "unread") + '" href="' + (n.link || "#") + '">' +
                                '<div><div class="n-title">' + n.title + '</div>' +
                                '<div class="n-msg">' + n.message + '</div>' +
                                '<div class="n-time">' + n.time + "</div></div></a>";
                        }).join("");
                    }
                }
            })
            .catch(function () { });
    }
    if (notifBell) {
        loadNotifications();
        setInterval(loadNotifications, 30000);
    }

    // ---- Mark notification read ----
    document.addEventListener("click", function (e) {
        var item = e.target.closest("[data-notif-read]");
        if (item) {
            fetch("/api/notifications/mark-read", {
                method: "POST",
                headers: { "X-CSRFToken": getCsrf(), "Content-Type": "application/json" },
                body: JSON.stringify({ id: item.getAttribute("data-notif-read") }),
            }).catch(function () { });
        }
    });

    // ---- Expose helpers ----
    window.RMS = { getCsrf: getCsrf, showToast: showToast };
})();
