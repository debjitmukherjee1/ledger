"""
fetch_prices.py — daily closes for a call's own ticker or its benchmark.

LIVE:  Yahoo Finance chart endpoint (no API key), one request per symbol.
MOCK:  deterministic synthetic series, anchored near the real call price, so
       Ledger builds and runs fully offline.

Yahoo chart endpoint:
  https://query1.finance.yahoo.com/v8/finance/chart/TCS.NS?range=2y&interval=1d
"""
import math
import random
from datetime import datetime, timedelta, timezone

import config

try:
    import requests
except ImportError:
    requests = None

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"


def _weekday_dates(start, end):
    dates, d = [], start
    while d <= end:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    return dates


def _mock_series(symbol, anchor_price, start, end):
    """Deterministic daily close series via geometric random walk, seeded on
    the symbol + start date and anchored at `anchor_price` on `start` so
    mock returns/alpha look plausible relative to the real call price."""
    rng = random.Random(symbol + start.isoformat())
    mu_d = rng.uniform(-0.0004, 0.0009)
    sig_d = rng.uniform(0.008, 0.018)
    dates = _weekday_dates(start, end)
    closes, price = [], anchor_price
    for _ in dates:
        price *= math.exp(rng.gauss(mu_d, sig_d))
        closes.append(round(price, 2))
    return [d.isoformat() for d in dates], closes


def _live_series(symbol):
    params = {"range": "2y", "interval": "1d"}
    headers = {"User-Agent": "Mozilla/5.0 (Ledger research tool)"}
    r = requests.get(CHART.format(sym=symbol), params=params, headers=headers, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    dates, out = [], []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        dates.append(datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat())
        out.append(round(c, 2))
    return dates, out


def fetch_series(symbol, anchor_price, start, end):
    """Returns (dates[], closes[]).
    MOCK: series spans exactly [start, end], anchored at anchor_price.
    LIVE: full ~2yr series from Yahoo (caller slices to the window it needs);
    raises on failure so the caller decides the fallback (never silently
    substitutes fabricated numbers for a real-fetch failure)."""
    if config.MOCK_MODE:
        return _mock_series(symbol, anchor_price, start, end)
    return _live_series(symbol)
