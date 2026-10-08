// TQQQ Midpoint ORB Quant Terminal Frontend Controller

let equityChartInstance = null;
let pnlChartInstance = null;
let dayOfWeekChartInstance = null;

let currentPnlView = "monthly"; // "monthly" or "weekly"
let cachedAnalyticsData = null;
let websocket = null;
let isStrategyRunning = false;
let currentStrategyState = null;
let lastIbkrReachable = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initModals();
  initCharts();
  loadConfig();
  loadStats();
  connectWebSocket();

  // On-demand IBKR check
  setTimeout(checkIbkrSocketPing, 800);
  const ibkrPill = document.getElementById("ibkr-pill-container");
  if (ibkrPill) {
    ibkrPill.style.cursor = "pointer";
    ibkrPill.addEventListener("click", () => {
      appendLogLine({ time: new Date().toLocaleTimeString(), level: "INFO", message: "Probing IBKR socket reachability..." });
      checkIbkrSocketPing();
    });
  }

  document.getElementById("btn-toggle-strategy").addEventListener("click", handleToggleStrategy);
  document.getElementById("btn-restart-strategy").addEventListener("click", handleRestartStrategy);
  document.getElementById("btn-flatten-now").addEventListener("click", handleFlattenNow);
  document.getElementById("btn-kill-strategy").addEventListener("click", handleKillStrategy);
  document.getElementById("cfg-transmit").addEventListener("change", updateTransmitMode);
  document.getElementById("btn-clear-console").addEventListener("click", () => {
    document.getElementById("terminal-body").innerHTML = "";
  });
  const resetBtn = document.getElementById("btn-reset-session");
  if (resetBtn) {
    resetBtn.addEventListener("click", handleResetSession);
  }
  const portSelect = document.getElementById("cfg-port");
  if (portSelect) {
    portSelect.addEventListener("change", () => {
      handlePortChange();
      checkIbkrSocketPing();
    });
  }
  document.getElementById("btn-toggle-monthly").addEventListener("click", () => switchPnlView("monthly"));
  document.getElementById("btn-toggle-weekly").addEventListener("click", () => switchPnlView("weekly"));
  document.getElementById("config-form").addEventListener("submit", handleSaveConfig);
  updateTransmitMode();
});

// Top Tabs Controller
function initTabs() {
  const liveTabBtn = document.getElementById("tab-btn-live");
  const backtestTabBtn = document.getElementById("tab-btn-backtest");
  const livePane = document.getElementById("pane-live");
  const backtestPane = document.getElementById("pane-backtest");

  if (!liveTabBtn || !backtestTabBtn) return;

  liveTabBtn.addEventListener("click", () => {
    liveTabBtn.classList.add("active");
    backtestTabBtn.classList.remove("active");
    livePane.classList.add("active");
    backtestPane.classList.remove("active");
  });

  backtestTabBtn.addEventListener("click", () => {
    backtestTabBtn.classList.add("active");
    liveTabBtn.classList.remove("active");
    backtestPane.classList.add("active");
    livePane.classList.remove("active");

    setTimeout(() => {
      if (equityChartInstance) equityChartInstance.resize();
      if (pnlChartInstance) pnlChartInstance.resize();
      if (dayOfWeekChartInstance) dayOfWeekChartInstance.resize();
    }, 60);
  });
}

// Modal Logic
function initModals() {
  const modal = document.getElementById("config-modal");
  const openBtn = document.getElementById("btn-config-toggle");
  const closeBtn = document.getElementById("btn-close-modal");
  const cancelBtn = document.getElementById("btn-cancel-modal");

  const openModal = () => {
    modal.hidden = false;
    modal.classList.add("open");
  };
  const closeModal = () => {
    modal.classList.remove("open");
    modal.hidden = true;
  };

  openBtn.addEventListener("click", openModal);
  closeBtn.addEventListener("click", closeModal);
  cancelBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
}

// Chart.js Visualizations
function initCharts() {
  // 1. Equity Curve Chart
  const eqCtx = document.getElementById("equityChart").getContext("2d");
  const eqGradient = eqCtx.createLinearGradient(0, 0, 0, 300);
  eqGradient.addColorStop(0, "rgba(99, 102, 241, 0.45)");
  eqGradient.addColorStop(1, "rgba(99, 102, 241, 0.0)");

  equityChartInstance = new Chart(eqCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Portfolio Equity ($)",
          data: [],
          borderColor: "#818cf8",
          backgroundColor: eqGradient,
          borderWidth: 2,
          fill: true,
          tension: 0.15,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: "#ffffff",
          pointHoverBorderColor: "#6366f1",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            label: (ctx) => `Equity: $${Number(ctx.raw).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.04)" },
          ticks: { color: "#64748b", maxTicksLimit: 8 },
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.04)" },
          ticks: {
            color: "#64748b",
            callback: (val) => `$${(val / 1000).toFixed(0)}k`,
          },
        },
      },
    },
  });

  // 2. Monthly / Weekly P&L Bar Chart
  const pnlCtx = document.getElementById("pnlChart").getContext("2d");
  pnlChartInstance = new Chart(pnlCtx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "P&L ($)",
          data: [],
          backgroundColor: [],
          borderRadius: 4,
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `Net P&L: $${Number(ctx.raw).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#64748b", maxTicksLimit: 12 },
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.04)" },
          ticks: {
            color: "#64748b",
            callback: (val) => `$${Number(val).toLocaleString()}`,
          },
        },
      },
    },
  });

  // 3. Day of Week Pattern Chart
  const dowCtx = document.getElementById("dayOfWeekChart").getContext("2d");
  dayOfWeekChartInstance = new Chart(dowCtx, {
    type: "bar",
    data: {
      labels: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      datasets: [
        {
          label: "Cumulative P&L ($)",
          data: [0, 0, 0, 0, 0],
          backgroundColor: [],
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `P&L: $${Number(ctx.raw).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#94a3b8", font: { weight: "600" } },
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.04)" },
          ticks: {
            color: "#64748b",
            callback: (val) => `$${(val / 1000).toFixed(0)}k`,
          },
        },
      },
    },
  });
}

// Data Fetching & Rendering
async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const data = await res.json();
    const params = data.strategy?.params || {};

    // Populate modal inputs
    document.getElementById("cfg-opening-range").value = params.opening_range_minutes || 15;
    document.getElementById("cfg-capital").value = data.signal_capital || 5000;
    document.getElementById("cfg-atr-min").value = params.or_atr_min || 0.20;
    document.getElementById("cfg-atr-max").value = params.or_atr_max || 0.35;
    document.getElementById("cfg-atr-lookback").value = params.atr_lookback || 20;
    document.getElementById("cfg-risk-trade").value = params.risk_per_trade || 0.006;
    document.getElementById("cfg-profit-target").value = params.profit_target_r || 10.0;
    document.getElementById("cfg-breakeven").value = params.breakeven_r || 6.0;
    document.getElementById("cfg-entry-cutoff").value = params.entry_cutoff_time || "10:30";
    document.getElementById("cfg-flatten").value = params.flatten_time || "15:30";

    // Update shares badge
    const cap = data.signal_capital || 5000;
    document.getElementById("hud-shares-badge").textContent = `Calculated Sizing ($${cap.toLocaleString()} basis)`;
    document.querySelector(".metric-label").textContent = `Opening Range (${params.opening_range_minutes || 15}m)`;
    const bandText = document.getElementById("gauge-band-text");
    if (bandText) {
      bandText.textContent = `Target Band: ${(params.or_atr_min || 0.20).toFixed(2)} — ${(params.or_atr_max || 0.35).toFixed(2)}`;
    }
    document.getElementById("hud-or-range").textContent = "--";
    document.getElementById("hud-or-bounds").textContent = "Waiting for completed opening range";
    document.getElementById("hud-atr").textContent = "--";
    document.getElementById("hud-or-mid").textContent = "--";

    handlePortChange();
  } catch (err) {
    console.error("Failed to load config:", err);
  }
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    cachedAnalyticsData = data;

    renderKPIs(data.summary);
    renderEquityCurve(data.equity_curve);
    renderPnlChart(data);
    renderDayOfWeek(data.day_of_week);
    renderRecentTrades(data.recent_trades);
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

function renderKPIs(summary) {
  if (!summary) return;

  document.getElementById("kpi-current-equity").textContent = `$${summary.current_equity.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  document.getElementById("kpi-return-pct").textContent = `+${summary.total_return_pct}%`;
  document.getElementById("kpi-start-date").textContent = `Started ${summary.start_date} ($${(summary.start_capital / 1000).toFixed(0)}k basis)`;

  const pnlEl = document.getElementById("kpi-total-pnl");
  pnlEl.textContent = (summary.total_pnl >= 0 ? "+$" : "-$") + Math.abs(summary.total_pnl).toLocaleString(undefined, { minimumFractionDigits: 0 });
  pnlEl.className = `kpi-value ${summary.total_pnl >= 0 ? "positive" : "danger"}`;

  document.getElementById("kpi-win-stats").textContent = `${summary.win_count.toLocaleString()} Wins / ${summary.loss_count.toLocaleString()} Losses`;
  document.getElementById("kpi-cagr").textContent = `${summary.cagr_pct}%`;
  document.getElementById("kpi-sharpe").textContent = `Sharpe ${summary.sharpe_ratio}`;
  document.getElementById("kpi-max-dd").textContent = `${summary.max_drawdown_pct}%`;
  document.getElementById("kpi-win-rate").textContent = `${summary.win_rate_pct}%`;
  document.getElementById("kpi-profit-factor").textContent = `PF ${summary.profit_factor}`;
  document.getElementById("kpi-total-trades").textContent = `${summary.total_trades.toLocaleString()} Trades (10R target)`;
}

function renderEquityCurve(equityData) {
  if (!equityChartInstance || !equityData || !equityData.length) return;

  equityChartInstance.data.labels = equityData.map((d) => d.date);
  equityChartInstance.data.datasets[0].data = equityData.map((d) => d.equity);
  equityChartInstance.update();
}

function renderPnlChart(analytics) {
  if (!pnlChartInstance || !analytics) return;

  const dataset = currentPnlView === "monthly" ? analytics.monthly_pnl : analytics.weekly_pnl;
  if (!dataset) return;

  const labels = dataset.map((d) => (currentPnlView === "monthly" ? d.month : d.week));
  const values = dataset.map((d) => d.pnl);
  const colors = values.map((v) => (v >= 0 ? "rgba(16, 185, 129, 0.85)" : "rgba(244, 63, 94, 0.85)"));

  pnlChartInstance.data.labels = labels;
  pnlChartInstance.data.datasets[0].data = values;
  pnlChartInstance.data.datasets[0].backgroundColor = colors;
  pnlChartInstance.update();
}

function switchPnlView(view) {
  currentPnlView = view;
  document.getElementById("btn-toggle-monthly").classList.toggle("active", view === "monthly");
  document.getElementById("btn-toggle-weekly").classList.toggle("active", view === "weekly");
  if (cachedAnalyticsData) {
    renderPnlChart(cachedAnalyticsData);
  }
}

function renderDayOfWeek(dowData) {
  if (!dayOfWeekChartInstance || !dowData) return;

  const values = dowData.map((d) => d.pnl);
  const colors = values.map((v) => (v >= 0 ? "rgba(99, 102, 241, 0.85)" : "rgba(244, 63, 94, 0.85)"));

  dayOfWeekChartInstance.data.datasets[0].data = values;
  dayOfWeekChartInstance.data.datasets[0].backgroundColor = colors;
  dayOfWeekChartInstance.update();

  // Populate cards
  const grid = document.getElementById("weekday-stats-grid");
  grid.innerHTML = "";
  dowData.forEach((item) => {
    const card = document.createElement("div");
    card.className = "weekday-card";
    const isPos = item.pnl >= 0;
    card.innerHTML = `
      <span class="weekday-name">${item.day.slice(0, 3)}</span>
      <span class="weekday-pnl ${isPos ? "positive" : "danger"}">${isPos ? "+$" : "-$"}${Math.abs(item.pnl).toLocaleString(undefined, { minimumFractionDigits: 0 })}</span>
      <span class="weekday-winrate">${item.win_rate}% Win (${item.trades})</span>
    `;
    grid.appendChild(card);
  });
}

function renderRecentTrades(trades) {
  const tbody = document.getElementById("trades-table-body");
  tbody.innerHTML = "";
  if (!trades || !trades.length) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:#64748b;">No trades executed yet.</td></tr>`;
    return;
  }

  trades.forEach((t) => {
    const tr = document.createElement("tr");
    const isPos = t.pnl >= 0;
    tr.innerHTML = `
      <td>${t.exit_time || t.date}</td>
      <td>${t.weekday.slice(0, 3)}</td>
      <td><span class="tag-side ${t.direction.toLowerCase()}">${t.direction}</span></td>
      <td>${t.shares}</td>
      <td>$${t.entry_price.toFixed(2)}</td>
      <td>$${t.exit_price.toFixed(2)}</td>
      <td>${t.reason}</td>
      <td class="${isPos ? "positive" : "danger"} font-bold">${isPos ? "+$" : "-$"}${Math.abs(t.pnl).toFixed(2)}</td>
      <td class="${isPos ? "positive" : "danger"}">${isPos ? "+" : ""}${t.pnl_pct.toFixed(2)}%</td>
    `;
    tbody.appendChild(tr);
  });
}

// WebSocket Connection & Real-time Live Stream
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/live`;

  websocket = new WebSocket(wsUrl);

  websocket.onopen = () => {
    updateServerStatus(true);
  };

  websocket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "init") {
        handleStateUpdate(msg.data.state);
        if (msg.data.logs) {
          msg.data.logs.forEach(appendLogLine);
        }
      } else if (msg.type === "log") {
        appendLogLine(msg.data);
      } else if (msg.type === "status" || msg.type === "state") {
        handleStateUpdate(msg.data);
      } else if (msg.type === "clear_logs") {
        document.getElementById("terminal-body").innerHTML = "";
      }
    } catch (e) {
      console.error("WS Parse error:", e);
    }
  };

  websocket.onclose = () => {
    updateServerStatus(false);
    updateIbkrStatus("STOPPED", false);
    setTimeout(connectWebSocket, 3000);
  };
}

function updateServerStatus(online) {
  const dot = document.getElementById("system-status-dot");
  const text = document.getElementById("system-status-text");
  if (!dot || !text) return;
  if (online) {
    dot.className = "live-dot active";
    text.textContent = "ONLINE";
  } else {
    dot.className = "live-dot danger";
    text.textContent = "OFFLINE";
  }
}

async function checkIbkrSocketPing() {
  if (isStrategyRunning) return;
  const port = document.getElementById("cfg-port") ? parseInt(document.getElementById("cfg-port").value, 10) : 7497;
  const host = "127.0.0.1";
  try {
    const res = await fetch(`/api/ibkr/ping?host=${host}&port=${port}`);
    const data = await res.json();
    lastIbkrReachable = data.reachable;
    updateIbkrStatus(currentStrategyState ? currentStrategyState.status : "STOPPED", false, port);
  } catch (e) {
    lastIbkrReachable = false;
    updateIbkrStatus("STOPPED", false, port);
  }
}

function updateIbkrStatus(status, isConnected, forcedPort) {
  const dot = document.getElementById("ibkr-status-dot");
  const text = document.getElementById("ibkr-status-text");
  if (!dot || !text) return;
  const port = forcedPort || (document.getElementById("cfg-port") ? document.getElementById("cfg-port").value : "7497");

  if (isConnected) {
    dot.className = "live-dot active";
    text.textContent = `CONNECTED (${port})`;
  } else if (status === "CONNECTING" || status === "STARTING") {
    dot.className = "live-dot warning";
    text.textContent = `CONNECTING (${port})...`;
  } else if (lastIbkrReachable === true) {
    dot.className = "live-dot active";
    text.textContent = `READY (${port} OPEN)`;
  } else if (status === "ERROR") {
    dot.className = "live-dot danger";
    text.textContent = `PORT ${port} CLOSED`;
  } else {
    dot.className = "live-dot";
    text.textContent = `OFFLINE (${port} CLOSED)`;
  }
}

function updateStrategyButton(status, state) {
  const btn = document.getElementById("btn-toggle-strategy");
  const btnText = document.getElementById("btn-strategy-text");
  if (!btn || !btnText) return;

  if (status === "STARTING" || status === "CONNECTING") {
    isStrategyRunning = true;
    btn.className = "btn btn-danger connecting";
    btn.disabled = false;
    btnText.textContent = "CANCEL CONNECTING";
  } else if (status === "STOPPING") {
    isStrategyRunning = true;
    btn.className = "btn btn-danger stopping";
    btn.disabled = false;
    btnText.textContent = "STOPPING... (FORCE KILL)";
  } else if (isActiveStatus(status)) {
    isStrategyRunning = true;
    btn.className = "btn btn-danger running";
    btn.disabled = false;
    btnText.textContent = "STOP STRATEGY";
  } else if (status === "ERROR") {
    isStrategyRunning = false;
    btn.className = "btn btn-warning error-state";
    btn.disabled = false;
    btnText.textContent = "RETRY CONNECTION";
  } else {
    isStrategyRunning = false;
    btn.className = "btn btn-action";
    btn.disabled = false;
    const isTransmit = document.getElementById("cfg-transmit") && document.getElementById("cfg-transmit").checked;
    btnText.textContent = isTransmit ? "ARM & TRANSMIT" : "RUN DRY CHECK";
  }
}

function appendLogLine(log) {
  const terminal = document.getElementById("terminal-body");
  const line = document.createElement("div");
  line.className = `log-line ${(log.level || "info").toLowerCase()}`;
  line.innerHTML = `
    <span class="log-time">[${log.time}]</span>
    <span class="log-msg">${escapeHtml(log.message)}</span>
  `;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function handleStateUpdate(state) {
  if (!state) return;
  currentStrategyState = state;

  const status = state.status || "STOPPED";
  const tag = document.getElementById("hud-signal-tag");
  tag.textContent = status;
  tag.className = `live-tag ${tagClassForStatus(status)}`;
  updateRunStatePanel(state);
  updateTimeline(status);

  updateIbkrStatus(status, state.ibkr_connected);
  updateStrategyButton(status, state);

  // Error handling
  if (state.error && status === "ERROR") {
    tag.textContent = "ERROR";
    tag.className = "live-tag danger";
  }

  // Update live TQQQ price
  if (state.last_price) {
    document.getElementById("tqqq-last-price").textContent = `$${state.last_price.toFixed(2)}`;
  }

  // Update recommendation HUD
  const rec = state.recommendation;
  if (rec) {
    document.getElementById("hud-or-range").textContent = `$${rec.or_range.toFixed(4)}`;
    document.getElementById("hud-or-bounds").textContent = `Low: ${rec.or_low.toFixed(2)} | High: ${rec.or_high.toFixed(2)}`;
    document.getElementById("hud-atr").textContent = rec.atr20 ? rec.atr20.toFixed(4) : "N/A";
    document.getElementById("hud-or-ratio").textContent = rec.ratio ? rec.ratio.toFixed(4) : "N/A";
    document.getElementById("hud-or-mid").textContent = `$${rec.or_mid.toFixed(2)}`;

    // Dynamic Filter Band Limits
    const rMin = rec.ratio_min != null ? rec.ratio_min : 0.15;
    const rMax = rec.ratio_max != null ? rec.ratio_max : 0.25;
    const bandText = document.getElementById("gauge-band-text");
    if (bandText) {
      bandText.textContent = `Target Band: ${rMin.toFixed(2)} — ${rMax.toFixed(2)}`;
    }

    // Dynamic Track Zones (scale from 0.05 to 0.45, span = 0.40)
    const scaleMin = 0.05;
    const scaleMax = 0.45;
    const span = scaleMax - scaleMin;
    const compW = Math.max(10, Math.min(50, ((rMin - scaleMin) / span) * 100));
    const sweetW = Math.max(15, Math.min(60, ((rMax - rMin) / span) * 100));
    const expW = Math.max(10, 100 - compW - sweetW);

    const compZone = document.getElementById("zone-compressed");
    const sweetZone = document.getElementById("zone-sweetspot");
    const expZone = document.getElementById("zone-expanded");
    if (compZone && sweetZone && expZone) {
      compZone.style.width = `${compW}%`;
      sweetZone.style.width = `${sweetW}%`;
      expZone.style.width = `${expW}%`;
    }

    // Dynamic Needle Position
    const ratio = rec.ratio || 0.20;
    const pct = Math.max(0, Math.min(100, ((ratio - scaleMin) / span) * 100));
    const needleEl = document.getElementById("gauge-needle");
    if (needleEl) {
      needleEl.style.left = `${pct}%`;
    }
    const needleLabel = document.getElementById("needle-val-label");
    if (needleLabel) {
      needleLabel.textContent = ratio.toFixed(4);
    }

    // Diagnostic Status Card
    const statusCard = document.getElementById("gauge-status-card");
    const statusIcon = document.getElementById("gauge-status-icon");
    const statusHead = document.getElementById("gauge-status-text");
    const statusDetail = document.getElementById("gauge-status-detail");

    if (rec.can_trade) {
      if (statusCard) statusCard.className = "gauge-status-card status-pass";
      if (statusIcon) statusIcon.textContent = "✅";
      if (statusHead) statusHead.textContent = `TRADE QUALIFIED — Volatility in Sweet Spot (${ratio.toFixed(4)})`;
      if (statusDetail) {
        statusDetail.textContent = `Morning range ($${rec.or_range.toFixed(2)}) is ${((ratio) * 100).toFixed(1)}% of 20-day ATR ($${rec.atr20.toFixed(2)}), cleanly within the ${rMin.toFixed(2)} - ${rMax.toFixed(2)} filter band. Order bracket submitted.`;
      }
    } else {
      if (statusCard) statusCard.className = "gauge-status-card status-fail";
      if (statusIcon) statusIcon.textContent = "⛔";
      if (statusHead && statusDetail) {
        if (ratio < rMin) {
          statusHead.textContent = `STAND DOWN — Volatility Compressed (${ratio.toFixed(4)} < Min ${rMin.toFixed(2)})`;
          statusDetail.textContent = `The opening range ($${rec.or_range.toFixed(2)}) is too tight relative to 20-day ATR ($${rec.atr20.toFixed(2)}). Trading tight morning ranges produces high-frequency whipsaw and false breakouts. Preserving capital.`;
        } else if (ratio > rMax) {
          statusHead.textContent = `STAND DOWN — Volatility Blown Out (${ratio.toFixed(4)} > Max ${rMax.toFixed(2)})`;
          statusDetail.textContent = `The opening range ($${rec.or_range.toFixed(2)}) is unusually wide relative to 20-day ATR ($${rec.atr20.toFixed(2)}). Breakouts from stretched ranges suffer late-entry exhaustion and sharp mean-reversion reversals. Preserving capital.`;
        } else if (rec.max_range_valid === false) {
          statusHead.textContent = `STAND DOWN — 2x Historical Opening Range Guard Triggered`;
          statusDetail.textContent = `Today's opening range ($${rec.or_range.toFixed(2)}) is more than double the 20-day average opening range ($${(rec.avg_opening_range * 2).toFixed(2)}). Extreme tail-risk open. Preserving capital.`;
        } else {
          statusHead.textContent = `STAND DOWN — Sizing / Risk Filter Triggered`;
          statusDetail.textContent = `Capital basis ($${rec.capital.toLocaleString()}) or risk budget insufficient to meet minimum share sizing. Preserving cash.`;
        }
      }
    }

    // Direction badge
    const biasBadge = document.getElementById("tqqq-bias-badge");
    if (biasBadge) {
      biasBadge.textContent = rec.direction > 0 ? "BIAS: BULLISH" : "BIAS: BEARISH";
      biasBadge.className = `ticker-bias-badge ${rec.direction > 0 ? "bullish" : "bearish"}`;
    }

    // Bracket details
    if (rec.order_side) document.getElementById("bracket-entry-side").textContent = rec.order_side;
    if (rec.entry != null) document.getElementById("bracket-entry-price").textContent = `$${rec.entry.toFixed(2)}`;
    if (rec.target != null) document.getElementById("bracket-target-price").textContent = `$${rec.target.toFixed(2)}`;
    if (rec.stop != null) document.getElementById("bracket-stop-price").textContent = `$${rec.stop.toFixed(2)}`;
    if (rec.breakeven_trigger != null) document.getElementById("bracket-be-price").textContent = `$${rec.breakeven_trigger.toFixed(2)}`;
    if (rec.shares != null && rec.capital != null) {
      document.getElementById("hud-shares-badge").textContent = `${rec.shares} Shares ($${rec.capital.toLocaleString()} basis)`;
    }
  } else {
    // Reset HUD when no recommendation
    document.getElementById("hud-or-ratio").textContent = "--";
    const needleEl = document.getElementById("gauge-needle");
    if (needleEl) needleEl.style.left = "50%";
    const needleLabel = document.getElementById("needle-val-label");
    if (needleLabel) needleLabel.textContent = "--";
    const statusCard = document.getElementById("gauge-status-card");
    if (statusCard) statusCard.className = "gauge-status-card";
    const statusIcon = document.getElementById("gauge-status-icon");
    if (statusIcon) statusIcon.textContent = "⚪";
    const statusHead = document.getElementById("gauge-status-text");
    if (statusHead) statusHead.textContent = "Awaiting market open or session data...";
    const statusDetail = document.getElementById("gauge-status-detail");
    if (statusDetail) {
      statusDetail.textContent = "The strategy evaluates opening volatility against your active parameter limits before committing capital.";
    }
  }

  // Update open position tracker
  const pos = state.position;
  if (pos && pos.shares !== 0) {
    const isLong = pos.shares > 0;
    document.getElementById("pos-status-text").textContent = `${isLong ? "LONG" : "SHORT"} ${Math.abs(pos.shares)} Shares @ $${pos.avg_cost.toFixed(2)}`;
    const pnlEl = document.getElementById("pos-unrealized-pnl");
    const pnl = pos.unrealized_pnl || 0.0;
    pnlEl.textContent = (pnl >= 0 ? "+$" : "-$") + Math.abs(pnl).toFixed(2);
    pnlEl.className = `pos-pnl-val mono ${pnl >= 0 ? "positive" : "danger"}`;
  } else {
    document.getElementById("pos-status-text").textContent = "FLAT (Waiting for entry trigger)";
    const pnlEl = document.getElementById("pos-unrealized-pnl");
    pnlEl.textContent = "$0.00";
    pnlEl.className = "pos-pnl-val mono";
  }
}

function isActiveStatus(status) {
  return ["STARTING", "CONNECTING", "POLLING", "BRACKET_SUBMITTED", "PENDING_ENTRY", "IN_TRADE", "STOPPING", "FLATTEN_REQUESTED"].includes(status);
}

function tagClassForStatus(status) {
  if (["IN_TRADE", "PENDING_ENTRY", "BRACKET_SUBMITTED"].includes(status)) return "active";
  if (["ERROR", "KILLED", "EXIT_STOP"].includes(status)) return "danger";
  if (["STAND_DOWN", "CANCELLED", "READY_DRY_RUN", "STOPPING"].includes(status)) return "warning";
  return "";
}

function updateRunStatePanel(state) {
  const status = state.status || "STOPPED";
  const stateValue = document.getElementById("run-state-value");
  const nextAction = document.getElementById("run-next-action");
  const dot = document.getElementById("state-dot");
  if (stateValue) stateValue.textContent = status.replaceAll("_", " ");
  if (nextAction) nextAction.textContent = state.next_action || "Review settings, then run a dry check.";
  if (dot) dot.className = `state-dot ${tagClassForStatus(status) || "neutral"}`;
}

function updateTimeline(status) {
  const stepMap = {
    STARTING: "preflight",
    CONNECTING: "preflight",
    POLLING: "signal",
    READY_DRY_RUN: "signal",
    STAND_DOWN: "signal",
    BRACKET_SUBMITTED: "entry",
    PENDING_ENTRY: "entry",
    CANCELLED: "entry",
    IN_TRADE: "manage",
    EXIT_PROFIT: "flatten",
    EXIT_STOP: "flatten",
    FLATTEN_REQUESTED: "flatten",
    FLATTENED: "flatten",
  };
  const active = stepMap[status] || "preflight";
  document.querySelectorAll(".timeline-step").forEach((el) => {
    el.classList.toggle("active", el.dataset.step === active);
  });
}

function updateTransmitMode() {
  const checked = document.getElementById("cfg-transmit").checked;
  const label = document.getElementById("transmit-mode-label");
  const sub = document.getElementById("transmit-mode-sub");
  const btnText = document.getElementById("btn-strategy-text");
  if (label) label.textContent = checked ? "Transmit" : "Dry run";
  if (sub) sub.textContent = checked ? "Orders can route to IBKR" : "No IBKR orders";
  if (!isStrategyRunning && btnText) btnText.textContent = checked ? "ARM & TRANSMIT" : "RUN DRY CHECK";
}

// Strategy Toggle Handler
async function handleToggleStrategy() {
  const btn = document.getElementById("btn-toggle-strategy");
  const btnText = document.getElementById("btn-strategy-text");
  const status = currentStrategyState ? (currentStrategyState.status || "STOPPED") : "STOPPED";

  // 1. If currently connecting or starting -> User clicked "CANCEL CONNECTING"
  if (status === "CONNECTING" || status === "STARTING") {
    btnText.textContent = "CANCELLING...";
    appendLogLine({
      time: new Date().toLocaleTimeString(),
      level: "WARN",
      message: "Connection abort requested by operator.",
    });
    try {
      const res = await fetch("/api/strategy/stop", { method: "POST" });
      const data = await res.json();
      if (data.state && data.state.state) {
        handleStateUpdate(data.state.state);
      } else {
        isStrategyRunning = false;
        updateTransmitMode();
      }
    } catch (e) {
      console.error(e);
      isStrategyRunning = false;
      updateTransmitMode();
    }
    return;
  }

  // 2. If stopping -> User clicked "STOPPING... (FORCE KILL)"
  if (status === "STOPPING") {
    btnText.textContent = "FORCE KILLING...";
    appendLogLine({
      time: new Date().toLocaleTimeString(),
      level: "ERROR",
      message: "Emergency kill forced by operator.",
    });
    try {
      const res = await fetch("/api/strategy/kill", { method: "POST" });
      const data = await res.json();
      if (data.state && data.state.state) handleStateUpdate(data.state.state);
    } catch (e) {
      console.error(e);
    }
    return;
  }

  // 3. If actively running (polling, in trade, etc.) -> User clicked "STOP STRATEGY"
  if (isActiveStatus(status)) {
    btnText.textContent = "STOPPING...";
    btn.className = "btn btn-danger stopping";
    try {
      const res = await fetch("/api/strategy/stop", { method: "POST" });
      const data = await res.json();
      if (data.state && data.state.state) {
        handleStateUpdate(data.state.state);
      } else {
        isStrategyRunning = false;
        updateTransmitMode();
      }
    } catch (err) {
      console.error("Failed to stop strategy:", err);
      isStrategyRunning = false;
      updateTransmitMode();
    }
    return;
  }

  // 4. Starting or Retrying from STOPPED / ERROR / STAND_DOWN
  const overrides = getFormData();

  // If retrying from ERROR, automatically step clientId to prevent any lingering Error 326 collision
  if (status === "ERROR") {
    overrides.client_id = (overrides.client_id || 45) + 1;
    const clientInput = document.getElementById("cfg-client-id");
    if (clientInput) clientInput.value = overrides.client_id;
    appendLogLine({
      time: new Date().toLocaleTimeString(),
      level: "INFO",
      message: `Retrying with fresh client ID: clientId=${overrides.client_id}...`,
    });
  }

  if (overrides.transmit) {
    const modeLabel = overrides.port === 7496 ? "LIVE" : "PAPER";
    const ok = window.confirm(`Transmit mode is enabled (${modeLabel} port ${overrides.port}). The dashboard may place and manage IBKR orders. Continue?`);
    if (!ok) {
      btnText.textContent = "ARM & TRANSMIT";
      return;
    }
  }

  // Warn operator if socket appears offline before starting
  if (lastIbkrReachable === false) {
    appendLogLine({
      time: new Date().toLocaleTimeString(),
      level: "WARN",
      message: `Warning: Port ${overrides.port} is closed. Make sure TWS/Gateway is running and API is enabled.`,
    });
  }

  // Optimistically switch button to Cancel Connecting
  isStrategyRunning = true;
  btn.className = "btn btn-danger connecting";
  btn.disabled = false;
  btnText.textContent = "CANCEL CONNECTING";

  appendLogLine({
    time: new Date().toLocaleTimeString(),
    level: "INFO",
    message: `Connecting to IBKR at ${overrides.host}:${overrides.port} (clientId=${overrides.client_id})...`,
  });

  try {
    const res = await fetch("/api/strategy/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(overrides),
    });
    const data = await res.json();
    if (data.status === "already_running") {
      appendLogLine({
        time: new Date().toLocaleTimeString(),
        level: "WARN",
        message: "Strategy was already running. Stopping previous run first...",
      });
      await fetch("/api/strategy/stop", { method: "POST" });
      isStrategyRunning = false;
      updateTransmitMode();
    } else if (data.state && data.state.state) {
      handleStateUpdate(data.state.state);
    }
  } catch (err) {
    console.error("Failed to start strategy:", err);
    appendLogLine({
      time: new Date().toLocaleTimeString(),
      level: "ERROR",
      message: `API request failed: ${err.message}`,
    });
    isStrategyRunning = false;
    updateTransmitMode();
  }
}

async function handleRestartStrategy() {
  const overrides = getFormData();
  const ok = window.confirm("Restart will stop the current dashboard worker, clear state, and start again with current settings. Continue?");
  if (!ok) return;
  try {
    const res = await fetch("/api/strategy/restart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(overrides),
    });
    const data = await res.json();
    appendLogLine({ time: new Date().toLocaleTimeString(), level: "WARN", message: "Restart requested from dashboard." });
    if (data.state && data.state.state) handleStateUpdate(data.state.state);
  } catch (err) {
    appendLogLine({ time: new Date().toLocaleTimeString(), level: "ERROR", message: `Restart failed: ${err.message}` });
  }
}

async function handleFlattenNow() {
  const ok = window.confirm("Flatten now will attempt to close any active TQQQ position through IBKR. Continue only if you have verified the current session.");
  if (!ok) return;
  try {
    const res = await fetch("/api/strategy/flatten", { method: "POST" });
    const data = await res.json();
    appendLogLine({ time: new Date().toLocaleTimeString(), level: "WARN", message: `Flatten requested: ${data.status}` });
    if (data.state && data.state.state) handleStateUpdate(data.state.state);
  } catch (err) {
    appendLogLine({ time: new Date().toLocaleTimeString(), level: "ERROR", message: `Flatten failed: ${err.message}` });
  }
}

async function handleKillStrategy() {
  const ok = window.confirm("Emergency kill disconnects the dashboard from IBKR. It does not guarantee external IBKR orders are cancelled. Verify TWS manually after killing. Continue?");
  if (!ok) return;
  try {
    const res = await fetch("/api/strategy/kill", { method: "POST" });
    const data = await res.json();
    appendLogLine({ time: new Date().toLocaleTimeString(), level: "ERROR", message: "Emergency kill requested from dashboard." });
    if (data.state && data.state.state) handleStateUpdate(data.state.state);
  } catch (err) {
    appendLogLine({ time: new Date().toLocaleTimeString(), level: "ERROR", message: `Kill failed: ${err.message}` });
  }
}

async function handleResetSession() {
  const btn = document.getElementById("btn-toggle-strategy");
  try {
    const res = await fetch("/api/strategy/reset", { method: "POST" });
    const data = await res.json();
    if (data.status === "reset_refused") {
      appendLogLine({
        time: new Date().toLocaleTimeString(),
        level: "WARN",
        message: "Reset refused while the strategy worker is active. Stop or kill first.",
      });
    } else {
      document.getElementById("terminal-body").innerHTML = "";
      appendLogLine({
        time: new Date().toLocaleTimeString(),
        level: "SUCCESS",
        message: "Live session state and logs successfully reset.",
      });
      isStrategyRunning = false;
      btn.classList.remove("running");
      btn.disabled = false;
      updateTransmitMode();
    }
    handleStateUpdate(data.state.state);
  } catch (err) {
    console.error("Failed to reset session:", err);
  }
}

function handlePortChange() {
  const port = parseInt(document.getElementById("cfg-port").value, 10);
  const warningEl = document.getElementById("live-port-warning");
  const offHoursCheck = document.getElementById("cfg-off-hours");
  const brokerPill = document.getElementById("broker-mode-pill");
  const brokerPillBox = document.getElementById("broker-mode-pill-box");

  if (port === 7496) {
    if (warningEl) warningEl.style.display = "block";
    if (offHoursCheck) {
      offHoursCheck.checked = false;
      offHoursCheck.disabled = true;
    }
    if (brokerPill) brokerPill.textContent = "IBKR Live (7496)";
    if (brokerPillBox) brokerPillBox.classList.add("live-mode");
  } else {
    if (warningEl) warningEl.style.display = "none";
    if (offHoursCheck) {
      offHoursCheck.disabled = false;
    }
    if (port === 4002) {
      if (brokerPill) brokerPill.textContent = "IB Gateway Paper (4002)";
    } else {
      if (brokerPill) brokerPill.textContent = "IBKR Paper (7497)";
    }
    if (brokerPillBox) brokerPillBox.classList.remove("live-mode");
  }
}

function getFormData() {
  return {
    host: document.getElementById("cfg-host").value || "127.0.0.1",
    opening_range_minutes: parseInt(document.getElementById("cfg-opening-range").value, 10),
    capital: parseFloat(document.getElementById("cfg-capital").value),
    or_atr_min: parseFloat(document.getElementById("cfg-atr-min").value),
    or_atr_max: parseFloat(document.getElementById("cfg-atr-max").value),
    atr_lookback: parseInt(document.getElementById("cfg-atr-lookback").value, 10),
    risk_per_trade: parseFloat(document.getElementById("cfg-risk-trade").value),
    profit_target_r: parseFloat(document.getElementById("cfg-profit-target").value),
    breakeven_r: parseFloat(document.getElementById("cfg-breakeven").value),
    entry_cutoff_time: document.getElementById("cfg-entry-cutoff").value,
    flatten_time: document.getElementById("cfg-flatten").value,
    port: parseInt(document.getElementById("cfg-port").value, 10),
    client_id: parseInt(document.getElementById("cfg-client-id").value, 10),
    account: document.getElementById("cfg-account").value.trim(),
    poll_seconds: parseInt(document.getElementById("cfg-poll-seconds").value, 10),
    off_hours_test: document.getElementById("cfg-off-hours").checked,
    transmit: document.getElementById("cfg-transmit").checked,
  };
}

async function handleSaveConfig(e) {
  e.preventDefault();
  const overrides = getFormData();
  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(overrides),
    });
    const data = await res.json();
    if (data.status === "ok") {
      const modal = document.getElementById("config-modal");
      modal.classList.remove("open");
      modal.hidden = true;
      loadConfig();
      // Show notification in terminal
      appendLogLine({
        time: new Date().toLocaleTimeString(),
        level: "SUCCESS",
        message: "Configuration saved and updated in configs/midpoint_stop_orb_intraday.yaml",
      });
    }
  } catch (err) {
    console.error("Failed to save config:", err);
  }
}
