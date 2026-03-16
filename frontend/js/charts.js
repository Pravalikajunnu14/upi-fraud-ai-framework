/**
 * charts.js
 * ---------
 * Chart.js configuration helpers for the UPI Shield dashboard.
 * All charts use the dark colour palette matching style.css.
 */

/* ── Global Chart.js defaults ─────────────────────────────────── */
Chart.defaults.color = "#94a3b8";
Chart.defaults.borderColor = "rgba(99,102,241,0.12)";
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.padding = 16;

/* ── Colour palette ───────────────────────────────────────────── */
const COLORS = {
    indigo: "#6366f1",
    purple: "#a855f7",
    pink: "#ec4899",
    cyan: "#22d3ee",
    green: "#22c55e",
    orange: "#f97316",
    red: "#ef4444",
    yellow: "#eab308",
};

function hexAlpha(hex, a) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${a})`;
}

/* ═══════════════════════════════════════════════════════════════
   DONUT CHART — Fraud vs Legitimate
════════════════════════════════════════════════════════════════ */
let donutChart = null;

function createDonutChart(fraud, legit) {
    const ctx = document.getElementById("chart-donut");
    if (!ctx) return;

    if (donutChart) donutChart.destroy();

    donutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Legitimate", "Fraud"],
            datasets: [{
                data: [legit, fraud],
                backgroundColor: [hexAlpha(COLORS.green, 0.8), hexAlpha(COLORS.red, 0.8)],
                borderColor: [COLORS.green, COLORS.red],
                borderWidth: 2,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            cutout: "70%",
            plugins: {
                legend: { position: "bottom" },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

function updateDonutChart(fraud, legit) {
    if (!donutChart) { createDonutChart(fraud, legit); return; }
    donutChart.data.datasets[0].data = [legit, fraud];
    donutChart.update("active");
}


/* ═══════════════════════════════════════════════════════════════
   BAR CHART — Fraud by Hour of Day
════════════════════════════════════════════════════════════════ */
let hourlyChart = null;

function createHourlyChart(data) {
    const ctx = document.getElementById("chart-hourly");
    if (!ctx) return;
    if (hourlyChart) hourlyChart.destroy();

    const labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    const gradient = ctx.getContext("2d").createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, hexAlpha(COLORS.indigo, 0.9));
    gradient.addColorStop(1, hexAlpha(COLORS.purple, 0.3));

    hourlyChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Fraud Transactions",
                data: data || Array(24).fill(0),
                backgroundColor: gradient,
                borderColor: COLORS.indigo,
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxRotation: 0, maxTicksLimit: 8 } },
                y: { beginAtZero: true, grid: { color: "rgba(99,102,241,0.08)" } }
            }
        }
    });
}

function updateHourlyChart(data) {
    if (!hourlyChart) { createHourlyChart(data); return; }
    hourlyChart.data.datasets[0].data = data;
    hourlyChart.update();
}


/* ═══════════════════════════════════════════════════════════════
   BAR CHART — Risk Level Breakdown
════════════════════════════════════════════════════════════════ */
let riskChart = null;

function createRiskChart(low, medium, high) {
    const ctx = document.getElementById("chart-risk");
    if (!ctx) return;
    if (riskChart) riskChart.destroy();

    riskChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Low Risk", "Medium Risk", "High Risk"],
            datasets: [{
                data: [low, medium, high],
                backgroundColor: [
                    hexAlpha(COLORS.green, 0.7),
                    hexAlpha(COLORS.orange, 0.7),
                    hexAlpha(COLORS.red, 0.7),
                ],
                borderColor: [COLORS.green, COLORS.orange, COLORS.red],
                borderWidth: 2,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: "rgba(99,102,241,0.08)" } }
            }
        }
    });
}

function updateRiskChart(low, medium, high) {
    if (!riskChart) { createRiskChart(low, medium, high); return; }
    riskChart.data.datasets[0].data = [low, medium, high];
    riskChart.update();
}


/* ═══════════════════════════════════════════════════════════════
   HORIZONTAL BAR — Feature Importance
════════════════════════════════════════════════════════════════ */
let featChart = null;

function createFeatureChart(features) {
    const ctx = document.getElementById("chart-features");
    if (!ctx || !features || !features.length) return;
    if (featChart) featChart.destroy();

    const labels = features.map(f => f.feature.replace(/_/g, " "));
    const values = features.map(f => (f.importance * 100).toFixed(2));
    const colors = features.map((_, i) => {
        const palette = [COLORS.indigo, COLORS.purple, COLORS.cyan, COLORS.pink,
        COLORS.orange, COLORS.green, COLORS.yellow, COLORS.red,
        COLORS.indigo, COLORS.purple];
        return hexAlpha(palette[i % palette.length], 0.8);
    });

    featChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Importance %",
                data: values,
                backgroundColor: colors,
                borderRadius: 4,
                borderSkipped: false,
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    beginAtZero: true, grid: { color: "rgba(99,102,241,0.08)" },
                    ticks: { callback: v => v + "%" }
                },
                y: { grid: { display: false } }
            }
        }
    });
}
