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
    renderEventsStrip();
  } catch (e) {
    console.error(e);
    document.getElementById("calls-tbody").innerHTML =
      `<tr><td colspan="11" class="muted">Could not load data. If running locally, serve with <code>python -m http.server</code>.</td></tr>`;
    const strip = document.getElementById("events-strip");
    if (strip) strip.innerHTML = "";
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
      <tr data-ticker="${c.ticker}">
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

// ---- next events strip --------------------------------------------------
// Calendar-day difference between the viewer's local "today" and an
// exchange-local YYYY-MM-DD date. Both sides are treated as date-only
// (via Date.UTC, ignoring time-of-day) so the count is a pure calendar-day
// diff and never shifts with the viewer's own timezone offset.
function daysToGo(dateStr) {
  const [y, m, d] = dateStr.split("-").map(Number);
  const eventUTC = Date.UTC(y, m - 1, d);
  const now = new Date();
  const todayUTC = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((eventUTC - todayUTC) / 86400000);
}

function daysLabel(days) {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days}d`;
}

// One entry per ticker: the row with the latest call_date represents the
// company (matches the row renderTable() would surface first for that
// ticker, since the table itself sorts call_date descending). The pipeline
// already drops past dates as of its last run, but that run could be up to
// a day stale by the time this loads -- so re-check "in the past" against
// the viewer's own clock too, and treat it the same as no date at all,
// rather than ever rendering a negative day-count as if it were current.
function nextEventsData() {
  const byTicker = new Map();
  for (const c of state.calls) {
    const cur = byTicker.get(c.ticker);
    if (!cur || c.call_date > cur.call_date) byTicker.set(c.ticker, c);
  }
  const items = [...byTicker.values()].map(c => {
    const ne = c.next_earnings;
    const days = ne ? daysToGo(ne.date) : null;
    return { ticker: c.ticker, company: c.company, next_earnings: days != null && days < 0 ? null : ne, days };
  });
  items.sort((a, b) => {
    const da = a.next_earnings && a.next_earnings.date;
    const db = b.next_earnings && b.next_earnings.date;
    if (da && db) return da.localeCompare(db);
    if (da) return -1;
    if (db) return 1;
    return a.company.localeCompare(b.company);
  });
  return items;
}

function renderEventsStrip() {
  const el = document.getElementById("events-strip");
  if (!el) return;
  const items = nextEventsData();
  el.innerHTML = items.map(it => {
    const ne = it.next_earnings;
    const days = ne ? it.days : null;
    const soon = days != null && days <= 7;
    const dateHtml = ne ? ne.date : `<span class="no-date">—</span>`;
    const daysHtml = days != null ? `<span class="event-days">${daysLabel(days)}</span>` : "";
    const title = ne ? `${ne.date} · source: ${ne.source} · as of ${ne.as_of || "—"}` : "No confirmed earnings date yet";
    return `
      <button type="button" class="event-chip${soon ? " soon" : ""}" data-ticker="${it.ticker}" title="${title}">
        <span class="event-ticker">${it.ticker}</span>
        <span class="event-date">${dateHtml}</span>
        ${daysHtml}
      </button>`;
  }).join("");
}

function scrollToTicker(ticker) {
  let row = document.querySelector(`#calls-tbody tr[data-ticker="${CSS.escape(ticker)}"]`);
  if (!row) {
    // The company's row may be hidden by the active filter -- reset to
    // "all" so it actually exists in the DOM, then try again.
    state.statusFilter = "all";
    state.marketFilter = "all";
    document.querySelectorAll("#status-filter button").forEach(b => b.classList.toggle("active", b.dataset.status === "all"));
    document.querySelectorAll("#market-filter button").forEach(b => b.classList.toggle("active", b.dataset.market === "all"));
    renderTable();
    row = document.querySelector(`#calls-tbody tr[data-ticker="${CSS.escape(ticker)}"]`);
  }
  if (!row) return;
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.classList.remove("row-flash");
  void row.offsetWidth; // restart the animation if the same row was just flashed
  row.classList.add("row-flash");
}

document.getElementById("events-strip").addEventListener("click", e => {
  const btn = e.target.closest(".event-chip");
  if (!btn) return;
  scrollToTicker(btn.dataset.ticker);
});

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
