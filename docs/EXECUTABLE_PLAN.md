# Ledger — Executable Plan

**Name:** Ledger *("A public, self-updating track record of every call I've published.")*
**Author:** Debjit Mukherjee
**Origin:** Third tool in the zero-cost GitHub-hosted finance suite, alongside Meridian and MarketPulse — same architecture, same visual identity, styled as a matching set.
**Status:** Working scaffold (this repo)

---

## 0. Cost & tokens (read first)

- **$0/day to run.** Hosting is GitHub Pages; the daily refresh runs on GitHub Actions (unlimited minutes for public repos); prices come from Yahoo Finance's free chart endpoint (no key, no secrets).
- **Zero Claude/Anthropic tokens in operation.** There is **no LLM in this tool at all** — it's a hand-maintained list of published calls plus daily arithmetic (return, alpha, distance to target). Claude was only used to build it.
- **The seed data is not fetched, it's authored.** `pipeline/calls.json` is the one part of Ledger that isn't automated — every entry traces back to an actual published report. The daily job only computes performance against that fixed record; it never invents or revises a call.

---

## 1. What it is

A public, audited-in-public scorecard for every rating I've published:

- **Rating** (BUY / HOLD / ACCUMULATE / REDUCE), **call date**, **price at call**, **target**, **live price**, **% return since call**, **alpha vs benchmark** (Nifty 50 for India names, S&P 500 for US names), **% distance to target**, and a **since-call sparkline** — one row per call.
- A **summary header**: total calls, hit rate on closed calls, average alpha, best call, worst call. Losers are shown exactly as prominently as winners — that's the entire premise.
- **Revisions are kept, not overwritten.** When a call is upgraded or downgraded (Infosys HOLD → ACCUMULATE, ICICI HOLD → REDUCE), both the closed original and the open revision stay in the record.

---

## 2. Why it stays free (the numbers)

| Component | Provider | Free limit | Our use |
|---|---|---|---|
| Hosting | GitHub Pages | 100 GB/mo bandwidth, unlimited static | a few dozen KB of JSON |
| Daily job | GitHub Actions | **Unlimited minutes (public repos)** | under a minute/day |
| Call + benchmark prices | Yahoo Finance chart endpoint | Free, no key | ~2 requests per call/day |

The website never calls an API at runtime — it reads pre-computed JSON. Marginal cost per visitor ≈ $0.

---

## 3. Architecture

```
        ┌──────────────────────────────────────────────┐
        │  GitHub Actions (cron, daily, free)          │
Yahoo ─▶│  fetch_prices.py → daily closes per call      │
        │            + its benchmark                   │
        │  run_all.py → return, alpha, target distance, │
        │               hit/miss on closed calls        │
        │        writes ▼                              │
        │  site/data/calls.json    (every call, enriched)│
        │  site/data/summary.json (hit rate, avg alpha…) │
        └───────────────────┬──────────────────────────┘
                            │ git push
                            ▼
        ┌──────────────────────────────────────────────┐
        │  GitHub Pages (static, free)                 │
        │  app.js → summary stats, filterable table,    │
        │           inline sparklines                  │
        └──────────────────────────────────────────────┘
```

`calls.json` in `pipeline/` is the hand-authored source of truth (every call, as published). The daily job reads it, fetches prices, and writes the *enriched* version to `site/data/` — the site only ever reads that computed output.

---

## 4. The math (methodology)

- **Return since call** — `(live_price / price_at_call − 1) × 100`. A **price return**: dividends are excluded, so income-paying names understate what a holder actually earned. Disclosed on the site.
- **Alpha** — the call's return since call date, minus its benchmark's return over the identical window, in the **same currency** (India calls vs Nifty 50 in INR, US calls vs S&P 500 in USD — never mixed).
- **Distance to target** — `(target / live_price − 1) × 100`. Positive: target still above the live price. Negative: live price has moved past it.
- **Hit / miss (closed calls only)** — a call closes when a later report revises it. Its window runs from its own call date to the revision date, using the revision's price as the closing price. Marked a **hit** if the price ever crossed the target during that window (reached it for an upside thesis, fell to it for a downside/fair-value thesis); otherwise a **miss**.
- **Summary stats** (hit rate, average alpha, best/worst call) are computed across every row — open and closed alike.

**Honest limits (stated on the Methodology tab):** prices refresh once daily from an unofficial free endpoint, not in real time. Price returns exclude dividends. Past calls are not a guarantee of future ones. Personal, educational tool — not investment advice, not SEBI-registered research.

---

## 5. Calls tracked (seed set)

TCS (BUY), HDFC Bank (HOLD), Infosys (HOLD → closed, revised to ACCUMULATE), ICICI Bank (HOLD → closed, revised to REDUCE), Amazon (BUY) — 7 records total. HUL, Alphabet, Apple, Tesla, Visa and Coca-Cola join once each is actually published; see `pipeline/calls.json` for the live list and `README.md` for how new calls get added.

---

## 6. Build phases

- **Phase 0 — repo:** push public repo, enable Pages via the Actions-based deploy (branch-deploy only supports `/` or `/docs`, not `/site` — `pages.yml` uses `upload-pages-artifact` instead, same as MarketPulse).
- **Phase 1 — data:** `python run_all.py` generates all JSON. Runs in mock mode offline; set `LEDGER_LIVE=1` for real Yahoo data.
- **Phase 2 — automate:** `daily-update.yml` refreshes and commits daily.
- **Phase 3 — grow:** add a new entry to `calls.json` each time a new call publishes; the cron does the rest.

---

## 7. What's in this scaffold

```
ledger/
├── docs/EXECUTABLE_PLAN.md      ← this file
├── site/                        ← GitHub Pages root
│   ├── index.html               ← 2 tabs: Track Record, Methodology
│   ├── css/styles.css           ← warm old-money theme (matches Meridian/MarketPulse)
│   ├── js/app.js                ← summary stats, filterable table, sparklines
│   ├── favicon.svg
│   └── data/                    ← generated JSON so it runs NOW
│       ├── calls.json           ← every call, enriched
│       └── summary.json         ← header stats
├── pipeline/
│   ├── calls.json               ← hand-authored source of truth (every published call)
│   ├── config.py                ← benchmarks, paths, mock/live switch
│   ├── fetch_prices.py          ← Yahoo (no key) + mock fallback
│   ├── run_all.py               ← return/alpha/target-distance/hit + write JSON
│   ├── requirements.txt
│   └── SOURCES.md
├── .github/workflows/
│   ├── daily-update.yml         ← cron: fetch + compute + commit site/data
│   └── pages.yml                ← deploys site/ via GitHub Actions (Pages'
│                                    branch-deploy only supports / or /docs,
│                                    not /site, so this uses upload-pages-artifact)
└── README.md
```

Everything runs offline in mock mode: `cd pipeline && python run_all.py`, then serve `site/`. Verified end-to-end — 7 calls, correct return/alpha/target-distance math, hit/miss computed on both closed calls.

---

## 8. Sources (verified July 2026)

- Yahoo Finance chart endpoint (free, no key): `https://query1.finance.yahoo.com/v8/finance/chart/TCS.NS`
- GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- GitHub Actions free & unlimited for public repos: https://docs.github.com/en/actions/concepts/billing-and-usage
