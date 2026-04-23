/* WATCHDOG Mission Control — SocketIO client.
   Subscribes to:
     system_status   — Kismet/BLE/GPS heartbeat
     device_update   — total/by-type counts
     detection       — new flagged detection (appended to detections panel)
     attack_alert    — deauth/disassoc/etc. — flashes the red banner
   All updates target IDs in templates/_panel_*.html. Edit those templates
   and this file to evolve the UI; no Python restart needed. */

(function () {
    "use strict";

    const socket = io();

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function setVisible(id, visible) {
        const el = document.getElementById(id);
        if (!el) return;
        if (visible) {
            el.classList.remove("hidden");
            el.style.removeProperty("display");
        } else {
            el.classList.add("hidden");
        }
    }

    socket.on("connect", function () {
        console.log("[mission-control] socket connected");
    });

    socket.on("disconnect", function () {
        console.log("[mission-control] socket disconnected");
        const badge = document.getElementById("kismet-badge");
        if (badge) {
            badge.textContent = "DASHBOARD: OFFLINE";
            badge.classList.add("badge-alpr");
            badge.classList.remove("badge-clear");
        }
    });

    socket.on("system_status", function (msg) {
        const badge = document.getElementById("kismet-badge");
        if (badge) {
            badge.textContent = "KISMET: " + (msg.kismet_up ? "LIVE" : "DOWN");
            badge.classList.toggle("badge-clear", !!msg.kismet_up);
            badge.classList.toggle("badge-alpr", !msg.kismet_up);
        }
        if (msg.last_update) setText("last-update", msg.last_update);
        if (msg.gps_lat !== null && msg.gps_lat !== undefined &&
            msg.gps_lon !== null && msg.gps_lon !== undefined) {
            setText("gps-lat", Number(msg.gps_lat).toFixed(4));
            setText("gps-lon", Number(msg.gps_lon).toFixed(4));
            setVisible("gps-line", true);
        }
        if (msg.coverage_area) {
            setText("coverage-area", msg.coverage_area);
            setVisible("coverage-area-wrap", true);
        }
        if (msg.nearby_alprs) {
            setText("nearby-alprs", msg.nearby_alprs);
            setVisible("nearby-alprs-wrap", true);
        }
    });

    socket.on("device_update", function (msg) {
        if (msg.count_total !== undefined) setText("stat-total", msg.count_total);
        if (msg.count_clean !== undefined) setText("stat-clean", msg.count_clean);
        const t = msg.by_type || {};
        if (t.cameras !== undefined)  setText("stat-cameras",  t.cameras);
        if (t.alpr !== undefined)     setText("stat-alprs",    t.alpr);
        if (t.drones !== undefined)   setText("stat-drones",   t.drones);
        if (t.ble_trackers !== undefined) setText("stat-trackers", t.ble_trackers);
        if (msg.count_total !== undefined) setText("all-devices-total", msg.count_total);
    });

    socket.on("detection", function (msg) {
        // Append a row to detections panel; cap at 50 visible.
        const body = document.getElementById("detections-body");
        if (!body) return;  // template might be in ALL CLEAR state
        const tr = document.createElement("tr");
        const klass = msg.type === "alpr" ? "alert-row"
                    : msg.type === "drone" ? "drone-row"
                    : "camera-row";
        tr.className = klass;
        tr.innerHTML =
            '<td><span class="badge badge-' + escapeHtml(msg.type) + '">' +
                escapeHtml((msg.type || "").toUpperCase()) + '</span></td>' +
            '<td>' + escapeHtml(msg.manufacturer || "") + '</td>' +
            '<td>' + escapeHtml(msg.mac || "") + '</td>' +
            '<td>' + escapeHtml(msg.ssid || "-") + '</td>' +
            '<td>' + escapeHtml(String(msg.signal ?? "")) + ' dBm</td>' +
            '<td>' + escapeHtml(String(msg.channel ?? "")) + '</td>' +
            '<td>' + (msg.confidence != null ? Math.round(msg.confidence * 100) + "%" : "") + '</td>' +
            '<td>' + escapeHtml(msg.source || "") + '</td>';
        body.insertBefore(tr, body.firstChild);
        while (body.children.length > 50) body.removeChild(body.lastChild);
        const count = document.getElementById("detections-count");
        if (count) count.textContent = body.children.length;
    });

    socket.on("attack_alert", function (msg) {
        // Show banner, populate text, auto-clear after 30 s of no follow-up.
        const banner = document.getElementById("attack-banner");
        const text = document.getElementById("attack-banner-text");
        if (banner && text) {
            text.textContent =
                (msg.attack_type || "ATTACK") + " from " + (msg.mac || "?") +
                " — " + (msg.reason || "");
            setVisible("attack-banner", true);
            clearTimeout(window.__attackBannerTimer);
            window.__attackBannerTimer = setTimeout(function () {
                setVisible("attack-banner", false);
            }, 30000);
        }

        // Append to attacks panel.
        const panel = document.getElementById("panel-attacks");
        const body = document.getElementById("attacks-body");
        if (panel && body) {
            setVisible("panel-attacks", true);
            const tr = document.createElement("tr");
            tr.className = "alert-row";
            const tsHuman = new Date((msg.ts || Date.now() / 1000) * 1000)
                .toLocaleTimeString();
            tr.innerHTML =
                '<td>' + escapeHtml(tsHuman) + '</td>' +
                '<td><span class="badge badge-attack">' + escapeHtml(msg.attack_type || "?") + '</span></td>' +
                '<td class="sev-' + escapeHtml(msg.severity || "med") + '">' +
                    escapeHtml((msg.severity || "med").toUpperCase()) + '</td>' +
                '<td>' + escapeHtml(msg.mac || "") + '</td>' +
                '<td>' + escapeHtml(String(msg.signal ?? "")) + ' dBm</td>' +
                '<td>' + escapeHtml(String(msg.count ?? 1)) + '</td>' +
                '<td>' + escapeHtml(msg.reason || "") + '</td>';
            body.insertBefore(tr, body.firstChild);
            while (body.children.length > 100) body.removeChild(body.lastChild);
            const count = document.getElementById("attacks-count");
            if (count) count.textContent = body.children.length;
        }
    });

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
})();
