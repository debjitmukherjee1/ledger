# Data source & cost (Ledger)

| Need | Source | Cost | Key? |
|---|---|---|---|
| Call prices + since-call series | **Yahoo Finance** chart endpoint | Free, no key | No |
| Benchmark prices (Nifty 50, S&P 500) | **Yahoo Finance** chart endpoint | Free, no key | No |
| Next earnings date | **Yahoo Finance** `quoteSummary` `calendarEvents` module, with a hand-maintained `pipeline/manual_events.json` fallback | Free, no key | No (session cookie + crumb, not an API key) |
| Hosting | GitHub Pages | Free | No |
| Daily refresh | GitHub Actions (public repo) | Free, unlimited minutes | No |

## Notes
- **No API key, no secrets.** Yahoo's chart endpoint (`query1.finance.yahoo.com/v8/finance/chart/<symbol>`) returns daily closes without authentication. One request per call's ticker plus one per benchmark, once a day. It is an *unofficial* endpoint, so the pipeline has a mock fallback and keeps yesterday's committed figures (marked stale) if a fetch fails.
- **Next earnings date** comes from Yahoo's `quoteSummary?modules=calendarEvents` endpoint (`pipeline/fetch_events.py`), which is even less stable than the chart endpoint: it requires a session cookie + crumb (undocumented gate) and rate-limits aggressively per IP. Any failure degrades to `null`, never a crash and never a stale date shown as current. `pipeline/manual_events.json` is a hand-maintained fallback keyed by `yahoo_symbol` — a manual entry always wins over Yahoo when present, and either way a date already in the past is dropped automatically. Every date on the site carries a `source` tag (`Yahoo` or `manual`) and the `as_of` date it was resolved.
- **Zero Claude/Anthropic tokens** in daily operation: there is no LLM in this tool at all. It's pure market data + arithmetic (returns, alpha, target distance).
- **Seed data (`calls.json`) is hand-maintained**, not fetched — every entry traces to a published research report. See the repo README for how new calls get added.

## Symbols in play
- India names: `TCS.NS`, `INFY.NS`, `HDFCBANK.NS`, `ICICIBANK.NS` — benchmark `^NSEI` (Nifty 50)
- US names: `AMZN` — benchmark `^GSPC` (S&P 500)
