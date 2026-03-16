/**
 * auth.js
 * -------
 * JWT authentication helpers used on every page.
 * - authFetch()  : wraps fetch() with the Bearer token header
 * - logout()     : clears token and redirects to login
 * - On page load : redirects to index.html if not logged in,
 *                  OR populates user info in the sidebar.
 */

const API_BASE = "http://localhost:5000";

// ── Token helpers ──────────────────────────────────────────────────
function getToken()          { return localStorage.getItem("upi_token"); }
function setToken(t)         { localStorage.setItem("upi_token", t); }
function clearToken()        { localStorage.removeItem("upi_token"); localStorage.removeItem("upi_user"); }
function getUser()           { return JSON.parse(localStorage.getItem("upi_user") || "null"); }
function setUser(u)          { localStorage.setItem("upi_user", JSON.stringify(u)); }

/**
 * Wrapper around fetch() that adds "Authorization: Bearer <token>" header.
 * Usage: const res = await authFetch("/api/dashboard/stats");
 */
async function authFetch(path, opts = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...(opts.headers || {}),
  };
    const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
    if (res.status === 401) {
        clearToken();
        window.location.href = "index.html";
    }
    return res;
}

function logout() {
  clearToken();
  window.location.href = "index.html";
}

// ── Login form handler (index.html) ───────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-login-submit");
  btn.textContent = "Signing in…";
  btn.disabled = true;

  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;

  try {
    const res  = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert(data.error || "Login failed", "error");
    } else {
      setToken(data.access_token);
      setUser(data.user);
      window.location.href = "dashboard.html";
    }
  } catch (err) {
    showAlert("Cannot connect to server. Is Flask running on port 5000?", "error");
  } finally {
    btn.textContent = "🔐  Sign In";
    btn.disabled = false;
  }
}

// ── Register form handler ──────────────────────────────────────────
async function handleRegister(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-reg-submit");
  btn.textContent = "Creating…";
  btn.disabled = true;

  const username = document.getElementById("reg-username").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const role     = document.getElementById("reg-role").value;

  try {
    const res  = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, email, role }),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert(data.error || "Registration failed", "error");
    } else {
      showAlert("Account created! Logging you in…", "success");
      // Auto-login after register
      setTimeout(async () => {
        document.getElementById("login-username").value = username;
        document.getElementById("login-password").value = password;
        switchTab("login");
        document.getElementById("form-login").dispatchEvent(
          Object.assign(new Event("submit"), { preventDefault: () => {} })
        );
        // Trigger manually
        const r2 = await fetch(`${API_BASE}/api/auth/login`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ username, password }),
        });
        const d2 = await r2.json();
        if (r2.ok) { setToken(d2.access_token); setUser(d2.user); window.location.href="dashboard.html"; }
      }, 900);
    }
  } catch {
    showAlert("Cannot connect to server.", "error");
  } finally {
    btn.textContent = "✨  Create Account";
    btn.disabled = false;
  }
}

// ── Tab switcher (index.html) ──────────────────────────────────────
function switchTab(tab) {
  document.getElementById("form-login").style.display    = tab === "login"    ? "" : "none";
  document.getElementById("form-register").style.display = tab === "register" ? "" : "none";
  document.getElementById("tab-login").classList.toggle("active",    tab === "login");
  document.getElementById("tab-register").classList.toggle("active", tab === "register");
}

// ── Alert helper (index.html) ──────────────────────────────────────
function showAlert(msg, type = "error") {
  const box = document.getElementById("alert-box");
  if (!box) return;
  box.className = `alert alert-${type}`;
  box.textContent = msg;
  box.style.display = "block";
  setTimeout(() => { box.style.display = "none"; }, 4000);
}

// ── Sidebar user info (dashboard/transactions pages) ───────────────
function populateSidebarUser() {
  const user = getUser();
  if (!user) return;
  const nameEl   = document.getElementById("user-name");
  const roleEl   = document.getElementById("user-role");
  const avatarEl = document.getElementById("user-avatar");
  if (nameEl)   nameEl.textContent   = user.username;
  if (roleEl)   roleEl.textContent   = user.role.toUpperCase();
  if (avatarEl) avatarEl.textContent = user.username[0].toUpperCase();
}

// ── Guard: redirect to login if token missing (dashboard pages) ────
(function initAuth() {
  const isLoginPage = window.location.pathname.endsWith("index.html")
                   || window.location.pathname === "/"
                   || window.location.pathname === "";

  if (!isLoginPage) {
    if (!getToken()) {
      window.location.href = "index.html";
      return;
    }
    populateSidebarUser();
  } else {
    // On login page: if already logged in, skip to dashboard
    if (getToken()) window.location.href = "dashboard.html";
  }
})();
