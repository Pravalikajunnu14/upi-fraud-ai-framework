/**
 * dashboard.js
 * ------------
 * Dashboard page logic:
 *  - Fetches and renders stat cards
 *  - Populates live transaction feed table
 *  - Creates and updates all charts via charts.js
 *  - Subscribes to Socket.IO live_transaction events
 *  - Renders the Leaflet.js fraud heatmap
 *  - Handles model retraining via admin button
 *  - Sends test email alert to logged-in user
 */

/* ── State ─────────────────────────────────────────────────────── */
let map = null;
let markers = [];
let liveFeedRows = [];

/* ── On load ───────────────────────────────────────────────────── */
window.addEventListener("DOMContentLoaded", async () => {
    await loadStats();
    await loadFeed();
    await loadCharts();
    await loadHeatmap();
    await loadModelMetrics();
    initLiveFeedSocket();
    checkModelStatus();

    // Auto-refresh stats + feed every 8 seconds
    setInterval(async () => {
        await loadStats();
        await loadFeed();
    }, 8000);
});

/* ── Stats ─────────────────────────────────────────────────────── */
async function loadStats() {
    try {
        const res = await authFetch("/api/dashboard/stats");
        if (!res.ok) return;
        const data = await res.json();

        setText("stat-total", data.total_transactions.toLocaleString());
        setText("stat-fraud", data.fraud_detected.toLocaleString());
        setText("stat-rate", data.fraud_rate + "%");
        setText("stat-blocked", data.blocked_transactions.toLocaleString());
        setText("stat-alerts", data.open_alerts.toLocaleString());
        setText("stat-avgscore", data.avg_fraud_score.toFixed(1) + "%");

        // Update donut + risk charts inline
        const total = data.total_transactions;
        updateDonutChart(data.fraud_detected, total - data.fraud_detected);

        const rd = data.risk_distribution || {};
        updateRiskChart(rd.Low || 0, rd.Medium || 0, rd.High || 0);
    } catch { }
}

/* ── Live Feed Table ───────────────────────────────────────────── */
async function loadFeed() {
    try {
        const res = await authFetch("/api/dashboard/feed");
        if (!res.ok) return;
        const data = await res.json();
        renderFeedRows(data.feed || []);
    } catch { }
}

function renderFeedRows(rows) {
    const tbody = document.getElementById("live-feed-body");
    if (!tbody) return;
    if (!rows.length) return;

    tbody.innerHTML = rows.slice(0, 20).map(r => `
    <tr>
      <td>${r.txn_id}</td>
      <td>₹${Number(r.amount).toLocaleString("en-IN")}</td>
      <td>${r.city}</td>
      <td>
        <div style="display:flex;align-items:center;gap:.5rem;">
          <span>${r.fraud_score}%</span>
          <div class="score-bar" style="width:60px;">
            <div class="score-fill ${r.risk_level ? r.risk_level.toLowerCase() : 'low'}"
                 style="width:${r.fraud_score}%"></div>
          </div>
        </div>
      </td>
      <td><span class="badge badge-${r.label === 'Fraud' ? 'fraud' : 'legit'}">${r.label}</span></td>
      <td><span class="badge badge-${(r.risk_level || '').toLowerCase()}">${r.risk_level || '—'}</span></td>
      <td style="color:#475569;font-size:.75rem;">${fmtTime(r.created_at)}</td>
    </tr>
  `).join("");
}

/* ── Charts ────────────────────────────────────────────────────── */
async function loadCharts() {
    // Hourly fraud
    try {
        const res = await authFetch("/api/dashboard/hourly");
        if (res.ok) {
            const data = await res.json();
            createHourlyChart(data.hourly_fraud);
        }
    } catch { }

    // Feature importance
    try {
        const res = await authFetch("/api/dashboard/feature-importance");
        if (res.ok) {
            const data = await res.json();
            createFeatureChart(data.feature_importance);
        }
    } catch { }
}

/* ── Heatmap (Leaflet.js) ──────────────────────────────────────── */
async function loadHeatmap() {
    const mapEl = document.getElementById("fraud-map");
    if (!mapEl) return;

    if (!map) {
        map = L.map("fraud-map", { zoomControl: true, attributionControl: false }).setView([22.0, 78.0], 5);
        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: "© CartoDB"
        }).addTo(map);
    }

    // Clear old markers
    markers.forEach(m => m.remove());
    markers = [];

    try {
        const res = await authFetch("/api/dashboard/heatmap");
        if (!res.ok) return;
        const data = await res.json();

        data.heatmap.forEach(pt => {
            if (!pt.latitude || !pt.longitude) return;
            const score = pt.fraud_score || 75;
            const color = score >= 65 ? "#ef4444" : score >= 30 ? "#f97316" : "#22c55e";

            const circle = L.circleMarker([pt.latitude, pt.longitude], {
                radius: 7, fillColor: color, color: "#fff",
                weight: 1, opacity: .9, fillOpacity: .75
            }).addTo(map);

            circle.bindPopup(`
        <div style="font-family:Inter,sans-serif;font-size:13px;">
          <strong>${pt.city}</strong><br/>
          Fraud Score: <strong>${score}%</strong>
        </div>
      `);
            markers.push(circle);
        });
    } catch { }
}

/* ── Model Metrics ─────────────────────────────────────────────── */
async function loadModelMetrics() {
    const container = document.getElementById("metric-cards");
    if (!container) return;
    try {
        const res = await authFetch("/api/dashboard/model-metrics");
        if (!res.ok) {
            container.innerHTML = `<p style="color:#64748b;grid-column:1/-1;">No model metrics found. Train the model first.</p>`;
            return;
        }
        const m = await res.json();
        const metrics = [
            { label: "Accuracy", value: pct(m.accuracy), icon: "🎯" },
            { label: "Precision", value: pct(m.precision), icon: "⚡" },
            { label: "Recall", value: pct(m.recall), icon: "🔍" },
            { label: "F1-Score", value: pct(m.f1_score), icon: "📊" },
            { label: "ROC-AUC", value: pct(m.roc_auc), icon: "📈" },
        ];
        container.innerHTML = metrics.map(m => `
      <div style="background:rgba(255,255,255,.04);border-radius:12px;padding:1rem;text-align:center;">
        <div style="font-size:1.5rem;">${m.icon}</div>
        <div style="font-size:1.3rem;font-weight:700;color:#f1f5f9;margin:.3rem 0;">${m.value}</div>
        <div style="font-size:.72rem;color:#64748b;">${m.label}</div>
      </div>
    `).join("");
    } catch { }
}

/* ── Retrain Model ─────────────────────────────────────────────── */
async function retrainModel() {
    const btn = document.getElementById("btn-retrain");
    const statusDiv = document.getElementById("retrain-status");
    if (btn) { btn.disabled = true; btn.textContent = "⏳ Retraining… (may take 1–2 min)"; }
    if (statusDiv) {
        statusDiv.style.display = "block"; statusDiv.innerHTML =
            `<div style="color:#a5b4fc;font-size:.85rem;">🤖 Generating new data and training model…</div>`;
    }

    try {
        const res = await authFetch("/api/model/retrain", { method: "POST" });
        const data = await res.json();
        if (res.ok) {
            if (statusDiv) statusDiv.innerHTML =
                `<div style="color:#86efac;font-size:.85rem;">✅ ${data.message}<br/>
         Accuracy: <strong>${pct(data.metrics?.accuracy)}</strong> &nbsp;|&nbsp;
         F1: <strong>${pct(data.metrics?.f1_score)}</strong></div>`;
            await loadModelMetrics();
            await loadCharts();
        } else {
            if (statusDiv) statusDiv.innerHTML =
                `<div style="color:#fca5a5;font-size:.85rem;">❌ ${data.error}</div>`;
        }
    } catch (e) {
        if (statusDiv) statusDiv.innerHTML =
            `<div style="color:#fca5a5;font-size:.85rem;">❌ Request failed: ${e.message}</div>`;
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = "🔄 Retrain Model"; }
    }
}

/* ── Test Alert Email ─────────────────────────────────────────── */
async function sendTestAlert() {
    const btn = document.getElementById("btn-test-alert");
    if (btn) { btn.disabled = true; btn.style.opacity = ".6"; btn.textContent = "⏳ Sending…"; }

    try {
        const res = await authFetch("/api/auth/test-alert", { method: "POST" });
        const data = await res.json();
        if (res.ok) {
            showToast(`✅ Test alert sent!<br><small>${data.recipient}</small>`, "success");
        } else if (res.status === 400) {
            showToast(`⚠️ ${data.error}`, "warn");
        } else {
            // Email credentials not configured
            showToast(`❌ Email not configured.<br><small>Fill ALERT_EMAIL_FROM &amp; ALERT_EMAIL_PASSWORD in .env</small>`, "error");
        }
    } catch (e) {
        showToast(`❌ Request failed: ${e.message}`, "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = "1";
            btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" style="width:16px;height:16px;"><path d="M1.5 8.67v8.58a3 3 0 003 3h15a3 3 0 003-3V8.67l-8.928 5.493a3 3 0 01-3.144 0L1.5 8.67z"/><path d="M22.5 6.908V6.75a3 3 0 00-3-3h-15a3 3 0 00-3 3v.158l9.714 5.978a1.5 1.5 0 001.572 0L22.5 6.908z"/></svg> Test Alert Email`;
        }
    }
}

/* ── Toast notification ────────────────────────────────────────── */
function showToast(html, type = "success") {
    // Remove existing toast
    const old = document.getElementById("alert-toast");
    if (old) old.remove();

    const colors = {
        success: { bg: "#166534", border: "#22c55e", text: "#bbf7d0" },
        warn:    { bg: "#78350f", border: "#f59e0b", text: "#fde68a" },
        error:   { bg: "#7f1d1d", border: "#ef4444", text: "#fca5a5" },
    };
    const c = colors[type] || colors.success;

    const toast = document.createElement("div");
    toast.id = "alert-toast";
    toast.innerHTML = html;
    Object.assign(toast.style, {
        position: "fixed", bottom: "1.5rem", right: "1.5rem",
        background: c.bg, border: `1px solid ${c.border}`, color: c.text,
        padding: "1rem 1.25rem", borderRadius: ".75rem",
        fontSize: ".88rem", lineHeight: "1.5", zIndex: "9999",
        maxWidth: "320px", boxShadow: "0 8px 32px rgba(0,0,0,.5)",
        animation: "slideUp .3s ease", fontFamily: "inherit"
    });
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

/* ── Socket.IO live feed ───────────────────────────────────────── */
function initLiveFeedSocket() {
    try {
        const socket = io("http://localhost:5000");
        socket.on("live_transaction", (data) => {
            const tbody = document.getElementById("live-feed-body");
            if (!tbody) return;

            // Remove old placeholder row
            const placeholder = tbody.querySelector("td[colspan]");
            if (placeholder) placeholder.parentElement.remove();

            const row = document.createElement("tr");
            row.style.animation = "slideUp .3s ease";
            row.innerHTML = `
        <td>${data.txn_id}</td>
        <td>₹${Number(data.amount).toLocaleString("en-IN")}</td>
        <td>${data.city}</td>
        <td>
          <div style="display:flex;align-items:center;gap:.5rem;">
            <span>${data.fraud_score}%</span>
            <div class="score-bar" style="width:60px;">
              <div class="score-fill ${(data.risk_level || '').toLowerCase()}" style="width:${data.fraud_score}%"></div>
            </div>
          </div>
        </td>
        <td><span class="badge badge-${data.label === 'Fraud' ? 'fraud' : 'legit'}">${data.label}</span></td>
        <td><span class="badge badge-${(data.risk_level || '').toLowerCase()}">${data.risk_level || '—'}</span></td>
        <td style="color:#475569;font-size:.75rem;">${fmtTime(data.timestamp)}</td>
      `;
            tbody.prepend(row);
            // Keep max 20 rows
            while (tbody.rows.length > 20) tbody.deleteRow(tbody.rows.length - 1);
        });
    } catch { }
}

/* ── Model status badge ─────────────────────────────────────────── */
async function checkModelStatus() {
    try {
        const res = await fetch("http://localhost:5000/api/health");
        const data = await res.json();
        const el = document.getElementById("model-status");
        if (el) {
            el.textContent = data.model_ready
                ? "🤖 Model: Ready"
                : "⚠️ Model: Not trained yet";
            el.style.color = data.model_ready ? "#86efac" : "#fdba74";
        }
    } catch { }
}

/* ── Helpers ───────────────────────────────────────────────────── */
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function pct(v) {
    return v != null ? (v * 100).toFixed(1) + "%" : "—";
}

function fmtTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso + (iso.endsWith("Z") ? "" : "Z"));
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
