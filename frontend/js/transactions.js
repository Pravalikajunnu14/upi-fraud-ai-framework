/**
 * transactions.js
 * ---------------
 * Transaction simulator page logic:
 *  - Submits transaction form to /api/transactions/check
 *  - Renders the animated SVG gauge with fraud score
 *  - Renders the result card (label, risk, recommendation)
 *  - Loads recent transaction history
 *  - Handles "Block" action on individual transactions
 *  - Quick preset buttons (Normal / Suspicious / High-Risk)
 */

const CITY_COORDS = {
    "Mumbai": [19.0760, 72.8777], "Delhi": [28.6139, 77.2090],
    "Bangalore": [12.9716, 77.5946], "Hyderabad": [17.3850, 78.4867],
    "Chennai": [13.0827, 80.2707], "Kolkata": [22.5726, 88.3639],
    "Pune": [18.5204, 73.8567], "Jaipur": [26.9124, 75.7873],
    "Ahmedabad": [23.0225, 72.5714], "Surat": [21.1702, 72.8311],
    "Lucknow": [26.8467, 80.9462], "Nagpur": [21.1458, 79.0882],
};

/* ── On load ───────────────────────────────────────────────────── */
window.addEventListener("DOMContentLoaded", () => {
    loadHistory();
    // Default form values
    const now = new Date();
    document.getElementById("f-hour").value = now.getHours();
    document.getElementById("f-avgamt").value = 5000;
    // Auto-detect user's real location on page load
    autoDetectCity();
});

/* ── Presets ───────────────────────────────────────────────────── */
function setPreset(type) {
    const presets = {
        normal: { amount: 1500, city: "Bangalore", hour: 14, newdev: "0", freq: 2, avg: 2000 },
        suspicious: { amount: 25000, city: "Mumbai", hour: 23, newdev: "1", freq: 6, avg: 4000 },
        fraud: { amount: 95000, city: "Delhi", hour: 3, newdev: "1", freq: 14, avg: 3000 },
    };
    const p = presets[type];
    if (!p) return;
    document.getElementById("f-amount").value = p.amount;
    document.getElementById("f-city").value = p.city;
    document.getElementById("f-hour").value = p.hour;
    document.getElementById("f-newdevice").value = p.newdev;
    document.getElementById("f-freq").value = p.freq;
    document.getElementById("f-avgamt").value = p.avg;
    document.getElementById("f-device").value = p.newdev === "1" ? `DEV_NEW_${Math.floor(Math.random() * 90000 + 10000)}` : `DEV_${Math.floor(Math.random() * 9000 + 1000)}`;
}

/* ── Submit Transaction ────────────────────────────────────────── */
async function submitTransaction(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-submit");
    btn.innerHTML = `<span class="spinner"></span> &nbsp;Analysing…`;
    btn.disabled = true;

    const city = document.getElementById("f-city").value;
    const coords = CITY_COORDS[city] || [19.076, 72.877];
    const amount = parseFloat(document.getElementById("f-amount").value);
    const avgamt = parseFloat(document.getElementById("f-avgamt").value) || amount;

    const payload = {
        upi_id: document.getElementById("f-upiid").value.trim(),
        amount,
        city,
        latitude: coords[0] + (Math.random() - .5) * .3,
        longitude: coords[1] + (Math.random() - .5) * .3,
        device_id: document.getElementById("f-device").value || `DEV_${Math.floor(Math.random() * 9000 + 1000)}`,
        is_new_device: parseInt(document.getElementById("f-newdevice").value),
    };

    const hour = parseInt(document.getElementById("f-hour").value);
    if (!isNaN(hour)) payload.hour = hour;

    const freq = parseInt(document.getElementById("f-freq").value);
    if (!isNaN(freq)) payload.transaction_frequency = freq;

    const userAvg = parseFloat(document.getElementById("f-avgamt").value);
    if (!isNaN(userAvg)) payload.user_avg_amount = userAvg;
    else payload.user_avg_amount = amount; // fallback to amount if no user avg


    try {
        const res = await authFetch("/api/transactions/check", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (!res.ok) {
            alert("Error: " + (data.error || data.msg || "Unknown error"));
            return;
        }
        renderResult(data);
        await loadHistory();
    } catch (err) {
        alert("Cannot connect to server: " + err.message);
    } finally {
        btn.innerHTML = "🔍 &nbsp;Analyse Transaction";
        btn.disabled = false;
    }
}

/* ── Render Result ─────────────────────────────────────────────── */
function renderResult(data) {
    // Show result, hide placeholder
    document.getElementById("result-placeholder").style.display = "none";
    const section = document.getElementById("result-section");
    section.style.display = "";

    const card = document.getElementById("result-card");
    card.className = `result-card ${data.label === "Fraud" ? "fraud-result" : "legit-result"}`;

    // Txn ID
    setText("result-txn-id", data.txn_id);

    // Gauge animation
    animateGauge(data.fraud_score, data.risk_level);

    // Result fields
    document.getElementById("r-label").innerHTML =
        `<span class="badge badge-${data.label === 'Fraud' ? 'fraud' : 'legit'}">${data.label}</span>`;
    document.getElementById("r-risk").innerHTML =
        `<span class="badge badge-${(data.risk_level || '').toLowerCase()}">${data.risk_level}</span>`;
    document.getElementById("r-amount").textContent =
        "₹" + Number(data.amount).toLocaleString("en-IN");
    document.getElementById("r-city").textContent = data.city;

    // Recommendation
    const recBox = document.getElementById("r-recommendation");
    recBox.className = `recommendation-box ${data.label === "Fraud" ? "rec-fraud" : "rec-legit"}`;
    recBox.innerHTML = data.recommendation;
}

/* ── Gauge animation ───────────────────────────────────────────── */
function animateGauge(score, riskLevel) {
    const path = document.getElementById("gauge-path");
    const numEl = document.getElementById("gauge-number");
    if (!path || !numEl) return;

    // The semicircle path length is ~251.3
    const total = 251.3;
    const offset = total - (score / 100) * total;
    path.style.strokeDashoffset = offset;

    // Color by risk
    const colors = { Low: "#22c55e", Medium: "#f97316", High: "#ef4444" };
    path.setAttribute("stroke", colors[riskLevel] || "#6366f1");

    // Animate number counter
    let current = 0;
    const target = Math.round(score);
    const step = Math.max(1, Math.floor(target / 40));
    const timer = setInterval(() => {
        current = Math.min(current + step, target);
        numEl.textContent = current;
        if (current >= target) clearInterval(timer);
    }, 20);
}

/* ── Load Transaction History ──────────────────────────────────── */
async function loadHistory() {
    try {
        const res = await authFetch("/api/transactions/?limit=10");
        if (!res.ok) return;
        const data = await res.json();
        renderHistory(data.transactions || []);
    } catch { }
}

function renderHistory(rows) {
    const tbody = document.getElementById("history-body");
    if (!tbody) return;
    if (!rows.length) return;

    tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.txn_id}</td>
      <td>₹${Number(r.amount).toLocaleString("en-IN")}</td>
      <td>${r.city}</td>
      <td>
        <div style="display:flex;align-items:center;gap:.5rem;">
          <span>${r.fraud_score}%</span>
          <div class="score-bar" style="width:55px;">
            <div class="score-fill ${(r.risk_level || '').toLowerCase()}"
                 style="width:${r.fraud_score}%"></div>
          </div>
        </div>
      </td>
      <td><span class="badge badge-${r.label === 'Fraud' ? 'fraud' : 'legit'}">${r.label}</span></td>
      <td><span class="badge badge-${(r.risk_level || '').toLowerCase()}">${r.risk_level || '—'}</span></td>
      <td style="color:#475569;font-size:.75rem;">${fmtTime(r.created_at)}</td>
      <td>
        ${r.is_blocked
            ? `<span class="badge badge-blocked">Blocked</span>`
            : (r.label === 'Fraud'
                ? `<button class="btn btn-danger" style="font-size:.72rem;padding:.25rem .65rem;"
                         onclick="blockTxn('${r.txn_id}', this)">🚫 Block</button>`
                : `<span style="color:#475569;font-size:.75rem;">—</span>`)
        }
      </td>
    </tr>
  `).join("");
}

/* ── Block a transaction ───────────────────────────────────────── */
async function blockTxn(txnId, btn) {
    if (!confirm(`Block transaction ${txnId}?`)) return;
    btn.disabled = true;
    try {
        const res = await authFetch(`/api/transactions/block/${txnId}`, { method: "POST" });
        const data = await res.json();
        if (res.ok) {
            btn.parentElement.innerHTML = `<span class="badge badge-blocked">Blocked</span>`;
        } else {
            alert(data.error);
            btn.disabled = false;
        }
    } catch {
        btn.disabled = false;
    }
}

/* ── Helpers ───────────────────────────────────────────────────── */
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

/* ── QR Code Scanner ──────────────────────────────────────────────── */
let qrScanner = null;

function openQRScanner() {
    document.getElementById("qr-modal").style.display = "block";
    document.getElementById("qr-status").textContent = "Starting camera…";
    qrScanner = new Html5Qrcode("qr-reader");
    qrScanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (decodedText) => { onQRSuccess(decodedText); },
        () => { }
    ).catch(err => {
        document.getElementById("qr-status").textContent = "⚠️ Camera error: " + err;
    });
}

function closeQRScanner() {
    if (qrScanner) {
        qrScanner.stop().catch(() => { });
        qrScanner = null;
    }
    document.getElementById("qr-modal").style.display = "none";
    document.getElementById("qr-reader").innerHTML = "";
}

function onQRSuccess(text) {
    closeQRScanner();
    // UPI deep-link format: upi://pay?pa=vpa@bank&pn=Name&am=500&cu=INR
    let upiId = "", amount = "";
    try {
        const url = new URL(text.startsWith("upi://") ? text.replace("upi://", "https://") : text);
        upiId = url.searchParams.get("pa") || "";
        amount = url.searchParams.get("am") || "";
    } catch {
        // Try raw parsing as query string
        const params = new URLSearchParams(text.includes("?") ? text.split("?")[1] : text);
        upiId = params.get("pa") || "";
        amount = params.get("am") || "";
    }
    if (upiId) document.getElementById("f-upiid").value = upiId;
    if (amount) document.getElementById("f-amount").value = amount;
    const msg = upiId ? `✅ QR scanned: ${upiId}${amount ? " | ₹" + amount : ""}` : "⚠️ Not a UPI QR code";
    document.getElementById("qr-status").textContent = msg;
    // Show status briefly below the modal
    const s = document.getElementById("qr-status");
    s.style.display = "block";
}

/* ── Auto-detect city via GPS + OpenStreetMap reverse geocode ──── */
async function autoDetectCity() {
    const cityInput = document.getElementById("f-city");
    const status = document.getElementById("location-status");

    if (!navigator.geolocation) {
        if (status) { status.textContent = "Geolocation not supported"; status.style.display = "block"; }
        return;
    }

    if (cityInput) cityInput.placeholder = "Detecting your location...";
    if (status) { status.textContent = "Detecting location..."; status.style.display = "block"; status.style.color = "#64748b"; }

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            const { latitude, longitude } = pos.coords;
            try {
                const url = `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`;
                const res = await fetch(url, { headers: { "Accept-Language": "en" } });
                const data = await res.json();
                const addr = data.address || {};
                const city = addr.city || addr.town || addr.village || addr.county || addr.state_district || addr.state || "Unknown";
                if (cityInput) cityInput.value = city;
                if (status) {
                    status.textContent = "Location detected: " + city;
                    status.style.color = "#86efac";
                    status.style.display = "block";
                    setTimeout(() => { status.style.display = "none"; }, 4000);
                }
            } catch {
                if (cityInput) cityInput.value = "Mumbai";
                if (status) { status.textContent = "Could not detect — defaulting to Mumbai"; status.style.color = "#f87171"; }
            }
        },
        () => {
            if (cityInput) { cityInput.value = "Mumbai"; cityInput.placeholder = "e.g. Mumbai"; }
            if (status) status.style.display = "none";
        },
        { timeout: 8000, enableHighAccuracy: true }
    );
}

function fmtTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso + (iso.endsWith("Z") ? "" : "Z"));
    return d.toLocaleString("en-IN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" });
}
