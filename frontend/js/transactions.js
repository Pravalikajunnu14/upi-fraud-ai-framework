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
    // Auto-detect real device ID on page load
    autoDetectDeviceId();
});

/* ── Real Device ID Detection ──────────────────────────────────── */
function getMobileDeviceInfo() {
    /**
     * Extract mobile-specific device information
     * Includes: Device model, manufacturer, OS version, etc.
     */
    const ua = navigator.userAgent;
    let mobileInfo = {
        brand: 'Unknown',
        model: 'Unknown',
        osVersion: 'Unknown',
        mobileId: 'UNKNOWN',
    };

    // Android detection
    if (ua.includes('Android')) {
        const androidMatch = ua.match(/Android ([0-9.]+)/);
        if (androidMatch) mobileInfo.osVersion = androidMatch[1];
        
        // Extract manufacturer and model
        // Examples:
        // Samsung: "Linux; Android 12; SM-A515F"
        // Xiaomi: "Linux; Android 11; M2102K1G"
        // OnePlus: "Linux; Android 12; DN2103"
        // Realme: "Linux; Android 12; RMX3361"
        
        const modelMatch = ua.match(/;\s*([A-Z][A-Z0-9\-]+)(?:\s|[;)])/);
        if (modelMatch) {
            mobileInfo.model = modelMatch[1];
            
            // Determine brand from model code
            if (mobileInfo.model.startsWith('SM-')) mobileInfo.brand = 'Samsung';
            else if (mobileInfo.model.startsWith('M')) mobileInfo.brand = 'Xiaomi';
            else if (mobileInfo.model.startsWith('DN') || mobileInfo.model.startsWith('IN')) mobileInfo.brand = 'OnePlus';
            else if (mobileInfo.model.startsWith('RMX')) mobileInfo.brand = 'Realme';
            else if (mobileInfo.model.startsWith('POT')) mobileInfo.brand = 'Motorola';
            else if (mobileInfo.model.startsWith('ONEPLUS')) mobileInfo.brand = 'OnePlus';
            else if (ua.includes('Samsung')) mobileInfo.brand = 'Samsung';
            else if (ua.includes('Xiaomi')) mobileInfo.brand = 'Xiaomi';
            else if (ua.includes('OPPO')) mobileInfo.brand = 'OPPO';
            else if (ua.includes('Vivo')) mobileInfo.brand = 'Vivo';
            else if (ua.includes('realme')) mobileInfo.brand = 'Realme';
        }
        
        // Generate Android ID-like identifier
        mobileInfo.mobileId = `ANDROID_${mobileInfo.brand.toUpperCase()}_${mobileInfo.model}_${mobileInfo.osVersion}`;
    }
    
    // iOS detection
    if (ua.includes('iPhone') || ua.includes('iPad')) {
        const iosMatch = ua.match(/OS ([0-9_]+)/);
        if (iosMatch) mobileInfo.osVersion = iosMatch[1].replace(/_/g, '.');
        
        if (ua.includes('iPhone 14')) mobileInfo.model = 'iPhone 14';
        else if (ua.includes('iPhone 13')) mobileInfo.model = 'iPhone 13';
        else if (ua.includes('iPhone 12')) mobileInfo.model = 'iPhone 12';
        else if (ua.includes('iPhone 11')) mobileInfo.model = 'iPhone 11';
        else if (ua.includes('iPhone X')) mobileInfo.model = 'iPhone X';
        else if (ua.includes('iPad Pro')) mobileInfo.model = 'iPad Pro';
        else if (ua.includes('iPad Air')) mobileInfo.model = 'iPad Air';
        else if (ua.includes('iPad Mini')) mobileInfo.model = 'iPad Mini';
        else if (ua.includes('iPad')) mobileInfo.model = 'iPad';
        else mobileInfo.model = 'iPhone';
        
        mobileInfo.brand = 'Apple';
        
        // Generate IDFA-like identifier
        mobileInfo.mobileId = `iOS_${mobileInfo.model.replace(/ /g, '_')}_${mobileInfo.osVersion}`;
    }

    return mobileInfo;
}

function generateHardwareId() {
    /**
     * Generate a hardware-like ID using available browser APIs
     * Combines multiple sources for better device identification
     */
    const hardware = {
        screen: `${screen.width}x${screen.height}x${screen.colorDepth}`,
        cores: navigator.hardwareConcurrency || 0,
        memory: navigator.deviceMemory || 0,
        language: navigator.language,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    };
    
    // Create a hash-like string from hardware
    const hwString = JSON.stringify(hardware);
    let hash = 0;
    for (let i = 0; i < hwString.length; i++) {
        const char = hwString.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
    }
    
    return Math.abs(hash).toString(16).substring(0, 12).toUpperCase();
}

function getWebGLFingerprint() {
    /**
     * Get GPU/WebGL info for device fingerprinting
     * Different GPUs have different capabilities
     */
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return 'NOWEBGL';
        const info = gl.getExtension('WEBGL_debug_renderer_info');
        if (!info) return 'NOINFO';
        const gpu = gl.getParameter(info.UNMASKED_RENDERER_WEBGL);
        return gpu ? gpu.substring(0, 30).replace(/ /g, '_') : 'UNKNOWN_GPU';
    } catch (e) {
        return 'WEBGL_ERROR';
    }
}

function getRealDeviceId() {
    /**
     * Generate real device fingerprint by combining:
     * - User Agent (device model, OS, browser)
     * - Screen resolution
     * - Browser language
     * - Timezone
     * - CPU cores
     * - Device memory
     * - WebGL fingerprint
     * - For Mobile: Device brand, model, Android ID, iOS IDFA
     */
    
    // Get mobile-specific info if on mobile device
    const mobileInfo = getMobileDeviceInfo();
    const isMobile = navigator.userAgent.match(/Mobile|Android|iPhone|iPad/i);
    
    const deviceInfo = {
        // Browser & OS info
        userAgent: navigator.userAgent,
        
        // Mobile-specific detection
        isMobile: !!isMobile,
        mobileOS: mobileInfo.brand,
        mobileModel: mobileInfo.model,
        mobileModelCode: mobileInfo.mobileId,
        osVersion: mobileInfo.osVersion,
        
        // Screen info
        screenResolution: `${screen.width}x${screen.height}`,
        screenColorDepth: screen.colorDepth,
        screenPixelDepth: screen.pixelDepth,
        devicePixelRatio: window.devicePixelRatio,
        
        // Language & Timezone
        language: navigator.language,
        languages: navigator.languages ? navigator.languages.join(',') : 'UNKNOWN',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        timezoneOffset: new Date().getTimezoneOffset(),
        
        // Hardware info
        hardwareCores: navigator.hardwareConcurrency || 'UNKNOWN',
        deviceMemory: navigator.deviceMemory || 'UNKNOWN',
        maxTouchPoints: navigator.maxTouchPoints || 0,
        
        // Fingerprinting
        hardwareId: generateHardwareId(),
        webglFingerprint: getWebGLFingerprint(),
    };

    // Extract device type from user agent
    let deviceType = 'DESKTOP';
    const ua = navigator.userAgent.toLowerCase();
    if (ua.includes('mobile') || ua.includes('android')) deviceType = 'MOBILE';
    if (ua.includes('iphone') || ua.includes('ipad')) deviceType = 'iOS';
    if (ua.includes('tablet')) deviceType = 'TABLET';
    
    // Extract OS
    let osType = 'UNKNOWN';
    if (ua.includes('windows')) osType = 'Windows';
    if (ua.includes('mac') && !ua.includes('iphone')) osType = 'macOS';
    if (ua.includes('linux') && !ua.includes('android')) osType = 'Linux';
    if (ua.includes('android')) osType = 'Android';
    if (ua.includes('iphone') || ua.includes('ipad')) osType = 'iOS';
    
    // Create appropriate device ID based on device type
    let realDeviceId;
    
    if (deviceType === 'MOBILE' || deviceType === 'iOS') {
        // Mobile-specific ID with real brand, model, and version
        const modelCode = mobileInfo.model.replace(/ /g, '_');
        const osVer = mobileInfo.osVersion.replace(/\./g, '_');
        realDeviceId = `${deviceType}_${mobileInfo.brand}_${modelCode}_${osVer}_${deviceInfo.hardwareId}`;
    } else {
        // Desktop/Tablet ID
        const hash = btoa(JSON.stringify(deviceInfo)).substring(0, 20);
        realDeviceId = `DEVICE_${deviceType}_${osType}_${hash}`;
    }
    
    return {
        id: realDeviceId,
        info: deviceInfo,
        mobileInfo: mobileInfo,
    };
}

function autoDetectDeviceId() {
    /**
     * Automatically detect and populate real device ID
     */
    const device = getRealDeviceId();
    const deviceIdField = document.getElementById("f-device");
    
    if (deviceIdField) {
        deviceIdField.value = device.id;
        // Add title showing full device info
        deviceIdField.title = JSON.stringify(device.info, null, 2);
    }
    
    // Update device info display box
    const info = device.info;
    
    // Check if mobile
    const isMobile = device.info.isMobile;
    
    if (isMobile && device.mobileInfo) {
        // MOBILE DEVICE - Show mobile-specific info
        const mobileInfo = device.mobileInfo;
        const osDisplay = document.getElementById("device-os");
        const screenDisplay = document.getElementById("device-screen");
        const memoryDisplay = document.getElementById("device-memory");
        const tzDisplay = document.getElementById("device-timezone");
        
        if (osDisplay) {
            osDisplay.innerHTML = `📱 <strong>${mobileInfo.brand}</strong> ${mobileInfo.model} | OS ${mobileInfo.osVersion}`;
        }
        
        if (screenDisplay) {
            screenDisplay.textContent = `📺 Screen: ${info.screenResolution} (${info.screenColorDepth}-bit, DPR: ${info.devicePixelRatio})`;
        }
        
        if (memoryDisplay) {
            const cores = info.hardwareCores !== 'UNKNOWN' ? `${info.hardwareCores} cores` : 'cores unknown';
            const memory = info.deviceMemory !== 'UNKNOWN' ? `${info.deviceMemory}GB RAM` : 'RAM unknown';
            memoryDisplay.textContent = `💾 ${memory}, 🖥️ CPU: ${cores}`;
        }
        
        if (tzDisplay) {
            tzDisplay.textContent = `🌍 Timezone: ${info.timezone} (UTC${info.timezoneOffset > 0 ? '-' : '+'}${Math.abs(Math.floor(info.timezoneOffset / 60))})`;
        }
        
        // Log mobile detection
        console.log('📱 MOBILE DEVICE DETECTED');
        console.log(`Brand: ${mobileInfo.brand}`);
        console.log(`Model: ${mobileInfo.model}`);
        console.log(`OS Version: ${mobileInfo.osVersion}`);
        console.log(`Mobile ID: ${mobileInfo.mobileId}`);
        
    } else {
        // DESKTOP/TABLET - Show desktop info
        const osDisplay = document.getElementById("device-os");
        const screenDisplay = document.getElementById("device-screen");
        const memoryDisplay = document.getElementById("device-memory");
        const tzDisplay = document.getElementById("device-timezone");
        
        const userAgent = info.userAgent;
        let osLabel = 'OS: Unknown';
        if (userAgent.includes('Windows')) osLabel = '🪟 OS: Windows';
        if (userAgent.includes('Mac')) osLabel = '🍎 OS: macOS';
        if (userAgent.includes('Linux') && !userAgent.includes('Android')) osLabel = '🐧 OS: Linux';
        
        if (osDisplay) osDisplay.textContent = osLabel;
        
        if (screenDisplay) {
            screenDisplay.textContent = `📺 Screen: ${info.screenResolution} (${info.screenColorDepth}-bit color)`;
        }
        
        if (memoryDisplay) {
            const cores = info.hardwareCores !== 'UNKNOWN' ? `${info.hardwareCores} cores` : 'cores unknown';
            const memory = info.deviceMemory !== 'UNKNOWN' ? `${info.deviceMemory}GB RAM` : 'RAM unknown';
            memoryDisplay.textContent = `💾 ${memory}, 🖥️ CPU: ${cores}`;
        }
        
        if (tzDisplay) {
            tzDisplay.textContent = `🌍 Timezone: ${info.timezone} (UTC${info.timezoneOffset > 0 ? '-' : '+'}${Math.abs(Math.floor(info.timezoneOffset / 60))})`;
        }
    }
    
    // Log for debugging
    console.log('📱 Real Device ID Detected:', device.id);
    console.log('📊 Device Info:', device.info);
}

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

/* ── Get Exact Time with Milliseconds ──────────────────────────── */
function getExactTime() {
    const now = new Date();
    const isoString = now.toISOString();  // ISO format with UTC
    const milliseconds = now.getTime();  // Milliseconds since epoch
    const timeString = now.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        fractionalSecondDigits: 3  // Include milliseconds
    });
    
    return {
        iso: isoString,           // "2026-03-28T15:45:30.123Z"
        milliseconds: milliseconds,  // 1711610730123
        formatted: timeString,    // "15:45:30.123"
    };
}

/* ── Submit Transaction ────────────────────────────────────────── */
async function submitTransaction(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-submit");
    const exactTime = getExactTime();  // 📊 CAPTURE EXACT TIME WITH MILLISECONDS
    
    btn.innerHTML = `<span class="spinner"></span> &nbsp;Getting location…`;
    btn.disabled = true;

    const amount = parseFloat(document.getElementById("f-amount").value);
    const avgamt = parseFloat(document.getElementById("f-avgamt").value) || amount;

    // ─── Auto-detect live location using browser geolocation ─────────────────
    let latitude = null;
    let longitude = null;
    let locationStatus = "Not Available";

    if (navigator.geolocation) {
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    timeout: 5000,
                    enableHighAccuracy: true,
                });
            });
            latitude = position.coords.latitude;
            longitude = position.coords.longitude;
            locationStatus = "Browser Geolocation";
            console.log(`📍 Current location: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`);
        } catch (err) {
            console.warn("🌐 Geolocation not available, using manual city:", err.message);
            // Fallback: Use city coordinates if provided
            const city = document.getElementById("f-city").value || "Mumbai";
            const coords = CITY_COORDS[city] || [19.076, 72.877];
            latitude = coords[0] + (Math.random() - 0.5) * 0.1;
            longitude = coords[1] + (Math.random() - 0.5) * 0.1;
            locationStatus = "Manual City";
        }
    } else {
        // Fallback for browsers without geolocation
        const city = document.getElementById("f-city").value || "Mumbai";
        const coords = CITY_COORDS[city] || [19.076, 72.877];
        latitude = coords[0] + (Math.random() - 0.5) * 0.1;
        longitude = coords[1] + (Math.random() - 0.5) * 0.1;
        locationStatus = "Default";
    }

    btn.innerHTML = `<span class="spinner"></span> &nbsp;Analysing…`;

    const payload = {
        upi_id: document.getElementById("f-upiid").value.trim(),
        amount,
        latitude,  // Live browser location
        longitude, // Live browser location
        device_id: document.getElementById("f-device").value || `DEV_${Math.floor(Math.random() * 9000 + 1000)}`,
        is_new_device: parseInt(document.getElementById("f-newdevice").value),
        user_avg_amount: avgamt,
        client_time_ms: exactTime.milliseconds,  // 📊 Include exact client time
        client_time_iso: exactTime.iso,         // 📊 ISO format timestamp
    };

    // Optional: manual city override
    const city = document.getElementById("f-city").value;
    if (city) payload.city = city;

    // Optional: manual frequency
    const freq = parseInt(document.getElementById("f-freq").value);
    if (!isNaN(freq)) payload.transaction_frequency = freq;

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

        // 📊 LOG EXACT TIME INFORMATION
        console.log("⏱️  EXACT TIME CAPTURED:");
        console.log("  Client Time (ISO):", exactTime.iso);
        console.log("  Client Time (MS):", exactTime.milliseconds);
        console.log("  Client Time (Formatted):", exactTime.formatted);
        console.log("  Server Time (ISO):", data.timestamp);
        console.log("  Server Time (Exact):", data.exact_time);
        console.log("  Server Time (Epoch MS):", data.timestamp_ms);
        console.log("  Server Time (Unix):", data.timestamp_epoch);

        // Add location source to the result
        data.location_source_status = locationStatus;
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
    
    // Show location with auto-detection info
    const locationInfo = `${data.city} 📍 (${data.location_source || 'Auto-detected'})`;
    document.getElementById("r-city").textContent = locationInfo;
    
    // Show coordinates
    if (data.latitude && data.longitude) {
        const coordsText = `Lat: ${data.latitude.toFixed(4)}, Lng: ${data.longitude.toFixed(4)}`;
        const coordsEl = document.createElement('div');
        coordsEl.style.fontSize = '0.85rem';
        coordsEl.style.opacity = '0.7';
        coordsEl.textContent = coordsText;
        if (document.getElementById("r-coords")) {
            document.getElementById("r-coords").textContent = coordsText;
        }
    }
    
    // Show auto-detected time with millisecond precision
    if (data.exact_time || data.timestamp) {
        const exactTimeStr = data.exact_time || data.timestamp;  // 📊 EXACT TIME with milliseconds
        const timeInfo = `${data.hour}:00 on ${data.day_of_week} (Exact: ${exactTimeStr})`;
        if (document.getElementById("r-time")) {
            document.getElementById("r-time").textContent = timeInfo;
        }
    }

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
