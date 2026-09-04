/* executive_dashboard.js — Milestone 4
   Renders Executive Dashboard charts from real API data and polls for
   live updates every 30 seconds (lightweight fetch-based polling). */

(function () {
  const charts = {};

  function colorSet(n) {
    const base = ["#6c5ce7", "#00d4ff", "#a855f7", "#22c55e", "#f59e0b", "#ef4444", "#ec4899", "#14b8a6"];
    return Array.from({ length: n }, (_, i) => base[i % base.length]);
  }

  function makeLine(ctx, labels, data, label) {
    return new Chart(ctx, {
      type: "line",
      data: { labels, datasets: [{ label, data, borderColor: "#6c5ce7", backgroundColor: "rgba(108,92,231,0.15)", tension: 0.35, fill: true }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
  }

  function makeBar(ctx, labels, data, label) {
    return new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ label, data, backgroundColor: colorSet(labels.length) }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
  }

  function makeDoughnut(ctx, labels, data) {
    return new Chart(ctx, {
      type: "doughnut",
      data: { labels, datasets: [{ data, backgroundColor: colorSet(labels.length) }] },
      options: { plugins: { legend: { position: "bottom" } } },
    });
  }

  async function fetchJSON(url) {
    try {
      const res = await fetch(url);
      const json = await res.json();
      return json.success ? json.data : null;
    } catch (e) {
      console.error("fetch failed", url, e);
      return null;
    }
  }

  // Milestone 2/3 legacy chart endpoints return the chart payload directly
  // (no {success, data} envelope) — fetch them as-is.
  async function fetchRaw(url) {
    try {
      const res = await fetch(url);
      return await res.json();
    } catch (e) {
      console.error("fetch failed", url, e);
      return null;
    }
  }

  function initStaticCharts() {
    const regTrend = window.__regTrend || { labels: [], data: [] };
    charts.reg = makeLine(document.getElementById("regTrendChart"), regTrend.labels, regTrend.data, "Registrations");

    const healthTrend = window.__healthTrend || { labels: [], data: [] };
    charts.health = makeLine(document.getElementById("healthTrendChart"), healthTrend.labels, healthTrend.data, "Health Score");
  }

  async function loadOperationsCharts() {
    const ops = await fetchRaw("/api/charts/operations");
    if (!ops) return;
    if (ops.venue_utilization && document.getElementById("venueUtilChart")) {
      charts.venue = makeBar(document.getElementById("venueUtilChart"), ops.venue_utilization.labels, ops.venue_utilization.data, "Utilization %");
    }
    if (ops.speaker_assignments && document.getElementById("speakerUtilChart")) {
      charts.speaker = makeBar(document.getElementById("speakerUtilChart"), ops.speaker_assignments.labels, ops.speaker_assignments.data, "Sessions Assigned");
    }
  }

  async function loadSponsorshipChart() {
    const data = await fetchRaw("/api/charts/sponsorship");
    if (!data || !data.status_distribution) return;
    charts.sponsor = makeDoughnut(document.getElementById("sponsorPipelineChart"), data.status_distribution.labels, data.status_distribution.data);
  }

  async function loadIncidentChart() {
    const data = await fetchRaw("/api/charts/incidents");
    if (!data || !data.by_priority) return;
    charts.incident = makeDoughnut(document.getElementById("incidentSeverityChart"), data.by_priority.labels, data.by_priority.data);
  }

  function updateHealthRing(score) {
    const circumference = 314;
    const offset = circumference - (circumference * score) / 100;
    const ring = document.getElementById("ringFg");
    if (ring) ring.setAttribute("stroke-dashoffset", offset);
    const val = document.getElementById("healthScoreVal");
    if (val) val.textContent = score;
  }

  async function refreshKPIs() {
    const summary = await fetchJSON("/api/intelligence/summary");
    if (!summary) return;
    updateHealthRing(summary.health_score);
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set("readinessVal", summary.readiness_score);
    set("kpiRegistrations", summary.totals.total_registrations);
    set("kpiAttendance", summary.totals.expected_attendance_pct + "%");
    set("kpiCheckin", summary.totals.checked_in);
    set("kpiVenue", summary.totals.venue_utilization_pct + "%");
    set("kpiIncidents", summary.totals.critical_incidents);
    set("kpiAlerts", summary.totals.active_alerts);
    set("execSummary", summary.executive_summary);

    const risks = await fetchJSON("/api/intelligence/risks");
    if (risks) set("kpiRiskLevel", risks.overall_risk_level);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initStaticCharts();
    loadOperationsCharts();
    loadSponsorshipChart();
    loadIncidentChart();
    // Poll KPIs every 30s so the dashboard updates without a manual refresh.
    setInterval(refreshKPIs, 30000);
  });
})();
