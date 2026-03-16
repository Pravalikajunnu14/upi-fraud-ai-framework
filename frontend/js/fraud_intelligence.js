/* =====================================================================
   fraud_intelligence.js  –  UPI Shield Fraud Intelligence Hub
   All data is simulated / demo-mode; swap fetch() calls for real API.
   ===================================================================== */

'use strict';

// ── Demo Data ────────────────────────────────────────────────────────────────

const QUEUE_DATA = [
  { id:'TXN-9821', vpa:'moneymule92@paytm',  amount:'₹45,000', score:97, risk:'high',   city:'Delhi',   time:'02:14 AM' },
  { id:'TXN-8743', vpa:'shop.quick@upi',      amount:'₹12,300', score:88, risk:'high',   city:'Mumbai',  time:'03:07 AM' },
  { id:'TXN-7632', vpa:'rahultrading@ybl',    amount:'₹8,500',  score:85, risk:'high',   city:'Chennai', time:'02:47 AM' },
  { id:'TXN-6514', vpa:'fastpay.deals@oksbi', amount:'₹3,200',  score:63, risk:'medium', city:'Pune',    time:'11:22 PM' },
  { id:'TXN-5409', vpa:'vendor.xyz@hdfcbank', amount:'₹1,800',  score:51, risk:'medium', city:'Kolkata', time:'10:55 PM' },
  { id:'TXN-4398', vpa:'store.local@icici',   amount:'₹950',    score:28, risk:'low',    city:'Jaipur',  time:'09:30 PM' },
];

const META_DATA = {
  'TXN-9821': { Amount:'₹45,000', VPA:'moneymule92@paytm', City:'Delhi', Time:'02:14 AM', Device:'Android (New)', Network:'Mobile Data', Risk:'97 / 100', Velocity:'8 txns in 1 hr' },
  'TXN-8743': { Amount:'₹12,300', VPA:'shop.quick@upi',    City:'Mumbai', Time:'03:07 AM', Device:'Unknown iOS',  Network:'VPN Detected', Risk:'88 / 100', Velocity:'3 txns in 30 min' },
  'TXN-7632': { Amount:'₹8,500',  VPA:'rahultrading@ybl',  City:'Chennai',Time:'02:47 AM', Device:'Android',      Network:'Mobile Data', Risk:'85 / 100', Velocity:'First-time payee' },
  'TXN-6514': { Amount:'₹3,200',  VPA:'shop.quick@oksbi',  City:'Pune',   Time:'11:22 PM', Device:'Desktop',      Network:'Broadband',   Risk:'63 / 100', Velocity:'Normal pattern' },
  'TXN-5409': { Amount:'₹1,800',  VPA:'vendor.xyz@hdfcbank',City:'Kolkata',Time:'10:55 PM',Device:'Android',      Network:'Wi-Fi',       Risk:'51 / 100', Velocity:'Normal pattern' },
  'TXN-4398': { Amount:'₹950',    VPA:'store.local@icici', City:'Jaipur', Time:'09:30 PM', Device:'iOS',          Network:'Wi-Fi',       Risk:'28 / 100', Velocity:'Regular payee' },
};

const BIO_DATA = {
  'TXN-9821': { typing:92, scroll:18, orient:77, pressure:88, tags:['Fast-typing','Landscape','High-pressure','Jailbroken?'] },
  'TXN-8743': { typing:78, scroll:30, orient:85, pressure:71, tags:['VPN Active','New Device','Touch Anomaly'] },
  'TXN-7632': { typing:65, scroll:55, orient:40, pressure:60, tags:['Night Session','Unfamiliar Location','Rapid Swipe'] },
  'TXN-6514': { typing:44, scroll:60, orient:30, pressure:45, tags:['Normal Speed','Known Device'] },
  'TXN-5409': { typing:30, scroll:70, orient:20, pressure:35, tags:['Regular Pattern','Trusted Device'] },
  'TXN-4398': { typing:22, scroll:80, orient:15, pressure:28, tags:['Matches History','Trusted Device','Low Risk'] },
};

// ── Animated Counter ──────────────────────────────────────────────────────────
function animateCounter(el, target, prefix = '', suffix = '', duration = 1400) {
  let start = 0;
  const step = target / (duration / 16);
  const timer = setInterval(() => {
    start = Math.min(start + step, target);
    el.textContent = prefix + (Number.isInteger(target) ? Math.round(start) : start.toFixed(1)) + suffix;
    if (start >= target) clearInterval(timer);
  }, 16);
}

function loadMetrics() {
  animateCounter(document.getElementById('m-capture'), 94.7, '', '%');
  animateCounter(document.getElementById('m-fpr'),     3.2,  '', '%');
  animateCounter(document.getElementById('m-revenue'), 12.4, '₹', 'L');
  animateCounter(document.getElementById('m-alerts'),  6,    '', '');
  animateCounter(document.getElementById('m-blocked'), 47,   '', '');
}

// ── Investigation Queue ───────────────────────────────────────────────────────
let activeCase = null;

function buildQueue() {
  const list = document.getElementById('queue-list');
  document.getElementById('queue-count').textContent = QUEUE_DATA.length + ' cases';
  QUEUE_DATA.forEach((c, i) => {
    const el = document.createElement('div');
    el.className = 'queue-item';
    el.id = 'qi-' + c.id;
    el.setAttribute('role', 'listitem');
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-label', `Case ${c.id}, risk ${c.risk}, score ${c.score}`);
    el.innerHTML = `
      <div class="queue-rank">${i + 1}</div>
      <div style="flex:1;min-width:0;">
        <div class="queue-vpa">${c.vpa}</div>
        <div class="queue-amt">${c.amount} · ${c.city} · ${c.time}</div>
      </div>
      <span class="risk-badge ${c.risk}">${c.score}</span>
      <button class="btn-investigate" onclick="investigateCase('${c.id}')" aria-label="Investigate case ${c.id}">Investigate</button>`;
    el.addEventListener('click', () => investigateCase(c.id));
    el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') investigateCase(c.id); });
    list.appendChild(el);
  });
}

function investigateCase(id) {
  // Highlight active
  document.querySelectorAll('.queue-item').forEach(el => el.classList.remove('active'));
  const qi = document.getElementById('qi-' + id);
  if (qi) qi.classList.add('active');
  activeCase = id;

  buildMeta(id);
  buildBiometrics(id);
}

// ── Metadata Panel ────────────────────────────────────────────────────────────
const RED_KEYS = ['Risk', 'Velocity', 'Network'];

function buildMeta(id) {
  const data = META_DATA[id];
  const list = document.getElementById('meta-list');
  list.innerHTML = '';
  Object.entries(data).forEach(([k, v]) => {
    const isFlag = RED_KEYS.some(r => v.toString().includes(r) || k === 'Risk' || (k === 'Network' && v !== 'Wi-Fi' && v !== 'Broadband') || (k === 'Velocity' && v.includes('First')));
    list.innerHTML += `
      <div class="meta-row" role="listitem">
        <span class="meta-key">${k}</span>
        <span class="meta-val ${isFlag ? 'flag-red' : ''}">${v}</span>
      </div>`;
  });
}

// ── Biometrics Panel ──────────────────────────────────────────────────────────
function bioColor(val) {
  if (val >= 70) return '#EF4444';
  if (val >= 45) return '#F59E0B';
  return '#22C55E';
}

function buildBiometrics(id) {
  const bio = BIO_DATA[id];
  const grid = document.getElementById('bio-grid');
  const bars = [
    { label:'Typing Speed Anomaly', val:bio.typing },
    { label:'Scroll Behavior Deviation', val:bio.scroll },
    { label:'Device Orientation Shift', val:bio.orient },
    { label:'Touch Pressure Score', val:bio.pressure },
  ];
  grid.innerHTML = bars.map(b => `
    <div class="bio-item">
      <div class="bio-label">
        <span>${b.label}</span>
        <span style="font-family:var(--ff-code);color:${bioColor(b.val)};">${b.val}%</span>
      </div>
      <div class="bio-bar-track">
        <div class="bio-bar-fill" style="width:0%;background:${bioColor(b.val)};" data-target="${b.val}"></div>
      </div>
    </div>`).join('') +
    `<div>
      <div style="font-size:.68rem;color:var(--muted);font-family:var(--ff-sans);margin-bottom:.4rem;">Session Fingerprint</div>
      <div class="bio-fingerprint">${bio.tags.map(t => `<span class="fp-chip">${t}</span>`).join('')}</div>
    </div>`;

  // Animate bars after paint
  requestAnimationFrame(() => {
    grid.querySelectorAll('.bio-bar-fill').forEach(fill => {
      setTimeout(() => { fill.style.width = fill.dataset.target + '%'; }, 60);
    });
  });
}

// ── Network Graph (Canvas) ────────────────────────────────────────────────────
let networkAnim;
const NODES = [
  { x:.18, y:.35, r:14, col:'#EF4444', lbl:'Mule A', suspicious:true  },
  { x:.35, y:.20, r:10, col:'#EF4444', lbl:'Mule B', suspicious:true  },
  { x:.55, y:.55, r:12, col:'#F59E0B', lbl:'Hub',    suspicious:true  },
  { x:.72, y:.30, r:9,  col:'#22C55E', lbl:'Safe 1', suspicious:false },
  { x:.82, y:.65, r:9,  col:'#22C55E', lbl:'Safe 2', suspicious:false },
  { x:.25, y:.70, r:11, col:'#EF4444', lbl:'Mule C', suspicious:true  },
  { x:.50, y:.85, r:8,  col:'#22C55E', lbl:'Safe 3', suspicious:false },
  { x:.10, y:.60, r:8,  col:'#F59E0B', lbl:'Risk',   suspicious:true  },
  { x:.65, y:.80, r:8,  col:'#22C55E', lbl:'Safe 4', suspicious:false },
  { x:.90, y:.45, r:7,  col:'#22C55E', lbl:'Safe 5', suspicious:false },
];
const EDGES = [
  [0,2,true],[1,2,true],[2,3,false],[2,5,true],[2,6,false],
  [7,0,true],[7,5,true],[3,4,false],[5,6,false],[4,9,false],[8,9,false],[3,9,false],
];
let tick = 0;

function drawNetwork() {
  const canvas = document.getElementById('network-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth; const H = canvas.offsetHeight;
  canvas.width = W; canvas.height = H;

  ctx.clearRect(0, 0, W, H);

  // Pulse offset for animation
  const pulse = Math.sin(tick * 0.04) * 0.5 + 0.5;

  // Draw edges
  EDGES.forEach(([a, b, sus]) => {
    const n1 = NODES[a], n2 = NODES[b];
    ctx.beginPath();
    ctx.moveTo(n1.x * W, n1.y * H);
    ctx.lineTo(n2.x * W, n2.y * H);
    ctx.strokeStyle = sus
      ? `rgba(239,68,68,${0.35 + pulse * 0.3})`
      : 'rgba(34,197,94,0.22)';
    ctx.lineWidth = sus ? 1.8 : 1;
    if (sus) { ctx.setLineDash([5, 4]); } else { ctx.setLineDash([]); }
    ctx.stroke();
    ctx.setLineDash([]);
  });

  // Draw nodes
  NODES.forEach(n => {
    const x = n.x * W, y = n.y * H;
    // Glow ring
    if (n.suspicious) {
      ctx.beginPath();
      ctx.arc(x, y, n.r + 5 + pulse * 4, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(239,68,68,${0.08 + pulse * 0.07})`;
      ctx.fill();
    }
    // Node circle
    ctx.beginPath();
    ctx.arc(x, y, n.r, 0, Math.PI * 2);
    ctx.fillStyle = n.col + '22';
    ctx.strokeStyle = n.col;
    ctx.lineWidth = 2;
    ctx.fill();
    ctx.stroke();
    // Label
    ctx.font = `600 ${Math.max(9, n.r * 0.7)}px Fira Sans, sans-serif`;
    ctx.fillStyle = 'rgba(255,255,255,0.75)';
    ctx.textAlign = 'center';
    ctx.fillText(n.lbl, x, y + n.r + 13);
  });

  document.getElementById('stream-count').textContent = `Nodes: ${NODES.length}`;
  tick++;
  networkAnim = requestAnimationFrame(drawNetwork);
}

// ── XAI Chart ─────────────────────────────────────────────────────────────────
function buildXAI() {
  const ctx = document.getElementById('xai-chart').getContext('2d');
  const features = ['Txn Amount','Time of Day','Payee Age','Velocity','Geo-Risk','Device','VPA Score','Behaviour'];
  const values   = [0.31, 0.22, 0.18, 0.17, 0.15, 0.12, 0.10, 0.07];
  const colors   = values.map(v => v >= 0.18 ? 'rgba(239,68,68,0.75)' : v >= 0.12 ? 'rgba(245,158,11,0.75)' : 'rgba(34,197,94,0.7)');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: features,
      datasets: [{ data: values, backgroundColor: colors, borderRadius: 5, borderSkipped: false }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 1200, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` SHAP weight: ${(ctx.raw * 100).toFixed(0)}%`
          },
          backgroundColor: 'rgba(10,15,30,.95)',
          borderColor: 'rgba(59,130,246,.3)',
          borderWidth: 1,
          bodyColor: '#94a3b8',
          titleColor: '#f0f6ff',
          titleFont: { family: 'Fira Code', size: 11 },
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,.05)' },
          ticks: { color: '#64748b', font: { family: 'Fira Code', size: 10 }, callback: v => (v * 100).toFixed(0) + '%' },
          border: { color: 'rgba(255,255,255,.08)' },
        },
        y: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { family: 'Fira Sans', size: 11 } },
          border: { color: 'transparent' },
        }
      }
    }
  });
}

function buildDecisionRules() {
  const rules = [
    { icon:'🔴', text:'<strong>Amount</strong> exceeds 4× user\'s average transaction value', weight:'+31%', cls:'triggered pos' },
    { icon:'🔴', text:'<strong>Time-of-day</strong> falls in fraud peak window (1–4 AM)', weight:'+22%', cls:'triggered pos' },
    { icon:'🔴', text:'<strong>First-time payee</strong> — no prior transaction history', weight:'+18%', cls:'triggered pos' },
    { icon:'🔴', text:'<strong>Velocity</strong> — 8+ transactions within 1 hour', weight:'+17%', cls:'triggered pos' },
    { icon:'🟡', text:'<strong>Geo-risk score</strong> of recipient region is elevated', weight:'+15%', cls:'triggered pos' },
    { icon:'🟢', text:'<strong>Device</strong> matches known registered device', weight:'−12%', cls:'safe neg' },
    { icon:'🟢', text:'<strong>Account age</strong> > 2 years — reduces risk', weight:'−10%', cls:'safe neg' },
  ];
  const el = document.getElementById('decision-rules');
  el.innerHTML = rules.map(r => `
    <div class="rule-row ${r.cls.split(' ')[0]}" role="listitem">
      <span class="rule-icon">${r.icon}</span>
      <span class="rule-text">${r.text}</span>
      <span class="rule-weight ${r.cls.split(' ')[1]}">${r.weight}</span>
    </div>`).join('');
}

// ── Auth guards (reuse existing auth.js helpers) ──────────────────────────────
function initAuth() {
  const token = localStorage.getItem('token');
  const user  = JSON.parse(localStorage.getItem('user') || '{}');
  if (!token) { window.location.href = 'index.html'; return; }
  const nameEl = document.getElementById('user-name');
  const roleEl = document.getElementById('user-role');
  const avEl   = document.getElementById('user-avatar');
  if (nameEl) nameEl.textContent = user.username || 'Analyst';
  if (roleEl) roleEl.textContent = user.role || 'admin';
  if (avEl)   avEl.textContent   = (user.username || 'A')[0].toUpperCase();
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = 'index.html';
}

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  try { initAuth(); } catch (_) {}
  loadMetrics();
  buildQueue();
  drawNetwork();
  buildXAI();
  buildDecisionRules();
  // Auto-select first case after a short delay
  setTimeout(() => investigateCase('TXN-9821'), 800);
});

window.addEventListener('beforeunload', () => {
  if (networkAnim) cancelAnimationFrame(networkAnim);
});
