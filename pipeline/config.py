"""
Ledger configuration — public track record of published research calls.

Data comes from Yahoo Finance (unofficial chart endpoint, no API key), matching
the zero-cost, no-secrets approach used by Meridian/MarketPulse. In MOCK_MODE
(default when offline) the pipeline generates deterministic synthetic series
anchored near each call's real price, so the whole site runs without any
network access.
"""
import json
import os
from datetime import date

# --- Benchmarks: display name (as used in calls.json) -> Yahoo symbol -------
BENCHMARK_SYMBOLS = {
    "Nifty 50": "^NSEI",
    "S&P 500": "^GSPC",
}

# --- Paths -------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
CALLS_FILE = os.path.join(BASE_DIR, "calls.json")
MANUAL_EVENTS_FILE = os.path.join(BASE_DIR, "manual_events.json")
DATA_DIR = os.path.join(BASE_DIR, "..", "site", "data")

# --- Mode ----------------------------------------------------------------
# Yahoo needs no key; we go "live" whenever network is intended. Set
# LEDGER_LIVE=1 in the GitHub Action; default here is mock for safe offline runs.
MOCK_MODE = os.environ.get("LEDGER_LIVE") != "1"


def load_calls():
    with open(CALLS_FILE) as f:
        return json.load(f)


def load_manual_events():
    """yahoo_symbol -> hand-maintained {"date", "as_of"} next-earnings entry.

    A missing file, a ticker not listed, or a still-blank seed placeholder
    ("YYYY-MM-DD") all just mean "no manual override" -- skipped, never a
    hard error, so an unfilled seed entry can't take down the daily run.
    Keys starting with "_" (e.g. "_readme") are ignored. "as_of" is
    validated the same way as "date": a maintainer who fills in a real date
    but forgets to also replace the seeded "YYYY-MM-DD" placeholder for
    as_of gets None back for it (renders as "--"), not the literal
    placeholder string shown to site visitors as if it were a real date.
    """
    if not os.path.exists(MANUAL_EVENTS_FILE):
        return {}
    with open(MANUAL_EVENTS_FILE) as f:
        raw = json.load(f)
    out = {}
    for symbol, entry in raw.items():
        if symbol.startswith("_") or not isinstance(entry, dict):
            continue
        date_str = entry.get("date", "")
        try:
            date.fromisoformat(date_str)
        except (ValueError, TypeError):
            continue
        as_of = entry.get("as_of")
        try:
            date.fromisoformat(as_of)
        except (ValueError, TypeError):
            as_of = None
        out[symbol] = {"date": date_str, "as_of": as_of}
    return out
