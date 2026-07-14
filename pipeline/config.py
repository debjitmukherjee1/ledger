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

# --- Benchmarks: display name (as used in calls.json) -> Yahoo symbol -------
BENCHMARK_SYMBOLS = {
    "Nifty 50": "^NSEI",
    "S&P 500": "^GSPC",
}

# --- Paths -------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
CALLS_FILE = os.path.join(BASE_DIR, "calls.json")
DATA_DIR = os.path.join(BASE_DIR, "..", "site", "data")

# --- Mode ----------------------------------------------------------------
# Yahoo needs no key; we go "live" whenever network is intended. Set
# LEDGER_LIVE=1 in the GitHub Action; default here is mock for safe offline runs.
MOCK_MODE = os.environ.get("LEDGER_LIVE") != "1"


def load_calls():
    with open(CALLS_FILE) as f:
        return json.load(f)
