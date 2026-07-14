"""
run_all.py — builds site/data for Ledger.

For each call in calls.json, computes:
  - live_price / as_of   : latest close (open calls) or the price/date the call
                            was frozen at when a later call superseded it (closed)
  - return_pct            : price return since call_date, dividend-agnostic
  - benchmark_return_pct   : same window, on the call's benchmark index
  - alpha                  : return_pct - benchmark_return_pct
  - target_distance_pct    : how far live_price sits from target (null if no target)
  - hit                    : closed calls only — did the price cross the target
                              at any point between call_date and the closing date?
  - series                 : since-call daily closes, for the sparkline

A "closed" call's closing price/date is the price_at_call/call_date of whichever
open call on the same ticker came after it (its revision). If a live fetch fails
for a given symbol, that call's previous committed figures are kept and marked
stale rather than silently overwritten with fabricated numbers.

Writes:
  site/data/calls.json     -> every call, enriched
  site/data/summary.json   -> total calls, hit rate (closed), average alpha, best/worst

Usage:  python run_all.py                 (mock, offline)
        LEDGER_LIVE=1 python run_all.py    (live, Yahoo)
"""
import json
import os
from datetime import date, datetime, timezone

import config
import fetch_prices

# Rough index levels so mock benchmark series look plausible.
MOCK_ANCHOR = {
    "^NSEI": 25500,
    "^GSPC": 7575,
}


def _d(s):
    return date.fromisoformat(s)


def _slice(dates, closes, start, end):
    out_d, out_c = [], []
    for d, c in zip(dates, closes):
        dd = _d(d)
        if start <= dd <= end:
            out_d.append(d)
            out_c.append(c)
    return out_d, out_c


def _nearest_on_or_before(dates, closes, target_date):
    """Latest available close on or before target_date (handles weekends/
    holidays where the exact call_date isn't a trading day)."""
    best = None
    for d, c in zip(dates, closes):
        dd = _d(d)
        if dd > target_date:
            continue
        if best is None or dd > _d(best[0]):
            best = (d, c)
    if best is None and dates:
        return dates[0], closes[0]
    return best


def find_successor(calls, call):
    """The open call (same ticker) with the earliest call_date after this
    one's — i.e. whatever revision superseded it."""
    candidates = [c for c in calls
                  if c["yahoo_symbol"] == call["yahoo_symbol"]
                  and c is not call
                  and c["status"] == "open"
                  and _d(c["call_date"]) > _d(call["call_date"])]
    if not candidates:
        return None
    return min(candidates, key=lambda c: _d(c["call_date"]))


def enrich(call, calls, today):
    symbol = call["yahoo_symbol"]
    bench_symbol = config.BENCHMARK_SYMBOLS[call["benchmark"]]
    call_date = _d(call["call_date"])

    if call["status"] == "closed":
        successor = find_successor(calls, call)
        end_date = _d(successor["call_date"]) if successor else today
        closing_price = successor["price_at_call"] if successor else None
    else:
        end_date = today
        closing_price = None

    dates, closes = fetch_prices.fetch_series(symbol, call["price_at_call"], call_date, end_date)
    bdates, bcloses = fetch_prices.fetch_series(
        bench_symbol, MOCK_ANCHOR.get(bench_symbol, 10000), call_date, end_date)

    s_dates, s_closes = _slice(dates, closes, call_date, end_date)
    if not s_closes:
        s_dates, s_closes = dates, closes

    price_now = closing_price if closing_price is not None else s_closes[-1]

    b_call = _nearest_on_or_before(bdates, bcloses, call_date)
    b_now = _nearest_on_or_before(bdates, bcloses, end_date)

    return_pct = round((price_now / call["price_at_call"] - 1) * 100, 2)
    benchmark_return_pct = round((b_now[1] / b_call[1] - 1) * 100, 2)
    alpha = round(return_pct - benchmark_return_pct, 2)

    target = call.get("target")
    target_distance_pct = round((target / price_now - 1) * 100, 2) if target else None

    hit = None
    if call["status"] == "closed" and target:
        window = s_closes or [call["price_at_call"]]
        if target >= call["price_at_call"]:
            hit = max(window) >= target       # upside thesis: did price ever reach target?
        else:
            hit = min(window) <= target       # downside/fair-value thesis: did price ever fall to target?

    enriched = dict(call)
    enriched.update({
        "live_price": price_now,
        "as_of": end_date.isoformat(),
        "return_pct": return_pct,
        "benchmark_return_pct": benchmark_return_pct,
        "alpha": alpha,
        "target_distance_pct": target_distance_pct,
        "hit": hit,
        "series": [{"d": d, "c": c} for d, c in zip(s_dates, s_closes)],
        "source": "mock" if config.MOCK_MODE else "live",
    })
    return enriched


def _key(call):
    return (call["yahoo_symbol"], call["call_date"])


def main():
    mode = "MOCK" if config.MOCK_MODE else "LIVE"
    print(f"=== Ledger pipeline ({mode}) ===")
    today = datetime.now(timezone.utc).date()
    updated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    calls = config.load_calls()

    prev_path = os.path.join(config.DATA_DIR, "calls.json")
    prev_by_key = {}
    if os.path.exists(prev_path):
        with open(prev_path) as f:
            prev_by_key = {_key(c): c for c in json.load(f).get("calls", [])}

    enriched_calls = []
    for call in calls:
        try:
            enriched_calls.append(enrich(call, calls, today))
        except Exception as e:
            prev = prev_by_key.get(_key(call))
            if prev:
                print(f"  ! {call['company']} ({call['call_date']}): fetch failed ({e}); keeping previous data, marked stale")
                prev["source"] = "stale"
                enriched_calls.append(prev)
            else:
                raise

    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(prev_path, "w") as f:
        json.dump({"updated_at": updated, "calls": enriched_calls}, f, indent=2)

    closed = [c for c in enriched_calls if c["status"] == "closed" and c["hit"] is not None]
    hit_rate = round(100 * sum(1 for c in closed if c["hit"]) / len(closed), 1) if closed else None
    avg_alpha = round(sum(c["alpha"] for c in enriched_calls) / len(enriched_calls), 2) if enriched_calls else 0
    best = max(enriched_calls, key=lambda c: c["alpha"]) if enriched_calls else None
    worst = min(enriched_calls, key=lambda c: c["alpha"]) if enriched_calls else None

    summary = {
        "updated_at": updated,
        "total_calls": len(enriched_calls),
        "closed_calls": len(closed),
        "hit_rate_pct": hit_rate,
        "average_alpha_pct": avg_alpha,
        "best_call": {"company": best["company"], "rating": best["rating"], "call_date": best["call_date"], "alpha": best["alpha"]} if best else None,
        "worst_call": {"company": worst["company"], "rating": worst["rating"], "call_date": worst["call_date"], "alpha": worst["alpha"]} if worst else None,
    }
    with open(os.path.join(config.DATA_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    for c in enriched_calls:
        print(f"  {c['company']:26s} {c['rating']:11s} ret {c['return_pct']:+7.2f}%  alpha {c['alpha']:+7.2f}%  "
              f"status {c['status']:7s}" + (f" hit={c['hit']}" if c["hit"] is not None else ""))
    print(f"Wrote {len(enriched_calls)} calls -> {os.path.normpath(config.DATA_DIR)}")


if __name__ == "__main__":
    main()
