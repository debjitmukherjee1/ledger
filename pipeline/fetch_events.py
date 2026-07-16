"""
fetch_events.py — next earnings date for a ticker.

LIVE: Yahoo's unofficial quoteSummary `calendarEvents` module. Unlike the
chart endpoint, it now gates on a session cookie + crumb, and is known to
rate-limit aggressively per IP (confirmed firsthand while building this:
even the chart endpoint 429'd after a handful of calls from one sandbox).
Any failure -- network error, 401/429, missing crumb, malformed/missing
field -- degrades to None. This function must never raise and must never
turn a stale cached value into a freshly-dated one.

MOCK: no network call at all (mirrors fetch_prices.py's MOCK_MODE gate);
callers fall through to manual_events.json / "--".

Yahoo endpoints involved:
  https://query2.finance.yahoo.com/v1/test/getcrumb   (session crumb)
  https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=calendarEvents
"""
from datetime import datetime, timezone

import config

try:
    import requests
except ImportError:
    requests = None

UA = "Mozilla/5.0 (Ledger research tool)"
CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb"
QUOTE_SUMMARY = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sym}"

_crumb_cache = {}  # per-process, so we authenticate once per pipeline run


def _get_crumb(session):
    if "crumb" in _crumb_cache:
        return _crumb_cache["crumb"]
    session.get("https://fc.yahoo.com", headers={"User-Agent": UA}, timeout=10)
    r = session.get(CRUMB_URL, headers={"User-Agent": UA}, timeout=10)
    r.raise_for_status()
    crumb = r.text.strip()
    if not crumb or crumb.startswith("<"):
        raise ValueError("no usable crumb in getcrumb response")
    _crumb_cache["crumb"] = crumb
    return crumb


def fetch_earnings_date(symbol):
    """Next earnings date as an ISO calendar-date string (exchange-local,
    per Yahoo), or None if unavailable. Never raises."""
    if config.MOCK_MODE or requests is None:
        return None
    try:
        session = requests.Session()
        crumb = _get_crumb(session)
        r = session.get(
            QUOTE_SUMMARY.format(sym=symbol),
            params={"modules": "calendarEvents", "crumb": crumb},
            headers={"User-Agent": UA},
            timeout=10,
        )
        r.raise_for_status()
        result = r.json()["quoteSummary"]["result"]
        if not result:
            return None
        earnings = (result[0].get("calendarEvents") or {}).get("earnings") or {}
        dates = earnings.get("earningsDate") or []
        raws = [d["raw"] for d in dates if "raw" in d]
        if not raws:
            return None
        # Yahoo sometimes returns a window (unconfirmed report-date range);
        # take the earliest. Always read `raw` back as UTC, never local
        # system time -- it's a Unix timestamp, and converting through the
        # runner's local timezone would shift the calendar date by a day
        # depending on where the pipeline happens to execute.
        return datetime.fromtimestamp(min(raws), tz=timezone.utc).date().isoformat()
    except Exception:
        return None
