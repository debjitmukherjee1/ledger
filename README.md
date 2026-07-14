# Ledger — A Public Track Record

*A public, self-updating track record of every research call I've published.*

Every rating I've published — BUY, HOLD, ACCUMULATE, REDUCE — tracked daily
against its live price and benchmark (Nifty 50 for India names, S&P 500 for
US names): return since call, alpha, distance to target, and hit rate on
closed calls. Losers are shown exactly as prominently as winners. Honesty is
the product.

> Third tool in the zero-cost GitHub-hosted finance suite — same architecture
> as **Meridian** and **MarketPulse**, styled to match them as a set.

**→ Full plan & methodology:** [`docs/EXECUTABLE_PLAN.md`](docs/EXECUTABLE_PLAN.md)

## Cost: $0/day, zero Claude tokens
The daily refresh runs on **GitHub's servers** (Actions cron) and pulls from
**Yahoo Finance** (no key). There is **no LLM in this tool at all** — it's a
hand-maintained list of published calls plus daily arithmetic. Claude was only
used to build it.

## How it stays free
- **Hosting:** GitHub Pages (static)
- **Daily job:** GitHub Actions (unlimited minutes for public repos)
- **Data:** Yahoo Finance chart endpoint — no API key, no secrets
- **Seed data:** `pipeline/calls.json` is hand-authored, not fetched — every
  entry traces back to an actual published report

## Run it locally (no keys needed)
```bash
# 1. generate sample data (mock mode, offline)
cd pipeline
pip install -r requirements.txt
python run_all.py
#    for real data instead:  LEDGER_LIVE=1 python run_all.py

# 2. serve the site
cd ../site
python -m http.server 8000
# open http://localhost:8000
```

## Go live
1. Push this repo to GitHub (public). **No secrets to configure.**
2. Settings → Pages → Build and deployment → **Source: GitHub Actions** (the
   `/site` subfolder isn't supported by branch-deploy, so `pages.yml` deploys
   it via `upload-pages-artifact` instead).
3. `daily-update.yml` refreshes every morning (runs with `LEDGER_LIVE=1`).

## Adding a new call
Every time a new rating publishes, add one entry to `pipeline/calls.json`:

```json
{
  "company": "...", "ticker": "...", "yahoo_symbol": "...",
  "market": "India | US", "benchmark": "Nifty 50 | S&P 500",
  "call_date": "YYYY-MM-DD", "rating": "BUY | HOLD | ACCUMULATE | REDUCE",
  "price_at_call": 0, "target": 0, "currency": "INR | USD",
  "report_url": "", "status": "open"
}
```

If the new call **revises** an earlier open one on the same ticker, just add
it — the pipeline automatically closes the earlier entry and uses the new
call's price/date as the closing point. Nothing is deleted from the record.
The next daily run (or `python run_all.py` locally) picks it up.

## Structure
```
docs/    → the executable plan
site/    → static website (GitHub Pages root); data/ holds the enriched JSON
pipeline/→ the daily Python job (Yahoo fetch + return/alpha/target-distance math)
.github/ → the free cron automation
```

⚠️ Personal, educational research tool. Returns shown are **price returns
only** — dividends excluded. Prices refresh daily from an unofficial free
endpoint, not in real time. **Not investment advice. Not a solicitation. Not
SEBI-registered research.**
