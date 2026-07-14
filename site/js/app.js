/* Ledger — 100% static. Reads pre-computed JSON; no API keys, no live server. */

const state = {
  calls: [],
  summary: null,
  statusFilter: "all",
  marketFilter: "all",
};

// ---- boot -------------------------------------------------------------
async function boot() {
  try {
    const [callsDoc, summary] = await Promise.all([
      fetch("data/calls.json").then(r => r.json()),
      fetch("data/summary.json").then(r => r.json()),
    ]);
    state.calls = callsDoc.calls;
    state.summary = summary;
    document.getElementById("updated-at").textContent = summary.updated_at || "—";
    renderSummary();
    renderTable();
  } catch (e) {
    console.error(e);
    document.getElementById("calls-tbody").innerHTML =
      `<tr><td colspan="11" class="muted">Could not load data. If running locally, serve with <code>python -m http.server</code>.</td></tr>`;
  }
}

// ---- helpers ------------------------------------------------------------
const pct = n => (n == null ? "—" : (n >= 0 ? "+" : "") + Number(n).toFixed(2) + "%");
const cls = n => n == null ? "" : n > 0.001 ? "pos" : n < -0.001 ? "neg" : "flat";
const ratingClass = r => "rating-" + r.toLowerCase();

function fmtPrice(value, currency) {
  const symbol = currency === "INR" ? "₹" : "$";
  const locale = currency === "INR" ? "en-IN" : "en-US";
  return symbol + Number(value).toLocaleString(locale, { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function sparkSvg(series) {
  if (!series || series.length < 2) return "";
  const closes = series.map(p => p.c);
  const w = 110, h = 32, pad = 3;
  const min = Math.min(...closes), max = Math.max(...closes);
  const range = (max - min) || 1;
  const stepX = (w - pad * 2) / (closes.length - 1);
  const points = closes.map((c, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((c - min) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const color = closes[closes.length - 1] >= closes[0] ? "var(--bull)" : "var(--bear)";
  return `<svg class="sparkline" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="Price trend since call date">
    <path class="line" d="M${points.join(" L")}" stroke="${color}" />
  </svg>`;
}

// ---- summary header -------------------------------------------------------
function renderSummary() {
  const s = state.summary;
  const stats = [
    ["Total calls", s.total_calls, ""],
    ["Hit rate (closed)", s.hit_rate_pct == null ? "—" : `${s.hit_rate_pct}%`, s.closed_calls ? `${s.closed_calls} closed` : "no closed calls yet"],
    ["Average alpha", pct(s.average_alpha_pct), ""],
    ["Best call", s.best_call ? `${s.best_call.company}` : "—", s.best_call ? `${s.best_call.rating} · ${pct(s.best_call.alpha)} alpha` : ""],
    ["Worst call", s.worst_call ? `${s.worst_call.company}` : "—", s.worst_call ? `${s.worst_call.rating} · ${pct(s.worst_call.alpha)} alpha` : ""],
  ];
  document.getElementById("summary-stats").innerHTML = stats.map(([label, val, sub]) => `
    <div class="stat">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${val}</div>
      ${sub ? `<div class="small muted">${sub}</div>` : ""}
    </div>`).join("");
}

// ---- table ------------------------------------------------------------
function filteredCalls() {
  return state.calls.filter(c => {
    if (state.statusFilter !== "all" && c.status !== state.statusFilter) return false;
    if (state.marketFilter !== "all" && c.market !== state.marketFilter) return false;
    return true;
  }).sort((a, b) => b.call_date.localeCompare(a.call_date));
}

function renderTable() {
  const rows = filteredCalls();
  const tbody = document.getElementById("calls-tbody");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="11" class="muted">No calls match this filter.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(c => {
    const targetCell = c.target
      ? fmtPrice(c.target, c.currency)
      : `<span class="no-target">No target (by design)</span>`;
    const distCell = c.target_distance_pct == null
      ? `<span class="no-target">—</span>`
      : `<span class="${cls(c.target_distance_pct)}">${pct(c.target_distance_pct)}</span>`;
    const hitBadge = c.status === "closed" && c.hit != null
      ? ` <span class="small ${c.hit ? "pos" : "neg"}">${c.hit ? "hit" : "miss"}</span>` : "";
    return `
      <tr>
        <td class="company-cell">
          <div class="company-name">${c.company}</div>
          <div class="company-sub">${c.ticker} · ${c.market}${c.report_url ? ` · <a href="${c.report_url}" target="_blank" rel="noopener">note</a>` : ""}</div>
        </td>
        <td><span class="rating-badge ${ratingClass(c.rating)}">${c.rating}</span></td>
        <td class="num">${c.call_date}</td>
        <td class="num">${fmtPrice(c.price_at_call, c.currency)}</td>
        <td class="num">${targetCell}</td>
        <td class="num">${fmtPrice(c.live_price, c.currency)}</td>
        <td class="num"><span class="${cls(c.return_pct)}">${pct(c.return_pct)}</span></td>
        <td class="num"><span class="${cls(c.alpha)}">${pct(c.alpha)}</span></td>
        <td class="num">${distCell}</td>
        <td class="num sparkline-cell">${sparkSvg(c.series)}</td>
        <td class="num"><span class="status-pill ${c.status === "open" ? "is-open" : ""}">${c.status}</span>${hitBadge}</td>
      </tr>`;
  }).join("");
}

// ---- filters ------------------------------------------------------------
document.getElementById("status-filter").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  document.querySelectorAll("#status-filter button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  state.statusFilter = btn.dataset.status;
  renderTable();
});
document.getElementById("market-filter").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  document.querySelectorAll("#market-filter button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  state.marketFilter = btn.dataset.market;
  renderTable();
});

// ---- tabs + sliding indicator ---------------------------------------------
const indicator = document.getElementById("tab-indicator");
function moveIndicator(tab) {
  indicator.style.left = tab.offsetLeft + "px";
  indicator.style.width = tab.offsetWidth + "px";
}
function positionIndicatorToActive() {
  const a = document.querySelector(".tab.active"); if (a) moveIndicator(a);
}
document.querySelectorAll(".tab").forEach(t => {
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(x => {
      x.classList.remove("active");
      x.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    t.classList.add("active");
    t.setAttribute("aria-selected", "true");
    document.getElementById(t.dataset.tab).classList.add("active");
    moveIndicator(t);
  });
});
window.addEventListener("resize", positionIndicatorToActive);
window.addEventListener("load", positionIndicatorToActive);

boot();
