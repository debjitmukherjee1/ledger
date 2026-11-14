"""
publish.py — what Ledger is allowed to publish.

Indian-market research calls stay private for 12 months after their call date
(reduces SEBI research-analyst exposure). pipeline/calls.json holds the US calls and calls.india.json.enc (encrypted) the Indian ones;
this module is the single gate between that complete input and the public
output in site/data. The portfolio site applies the same 365-day rule.

  is_publishable(call, today) -> bool
  publishable(calls, today)   -> the calls that may appear on the site
  build_summary(calls, updated) -> summary.json payload, computed ONLY from the
                                   calls passed in (so a hidden call can never
                                   surface as "best"/"worst" or move an average)

Run directly to re-filter the already-built site/data in place (no network):
    python publish.py
The daily workflow runs this after run_all.py as a belt-and-braces guard.
"""
import json
import os
from datetime import date, datetime, timedelta, timezone

INDIA_EMBARGO_DAYS = 365

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "data")


def is_india(call):
    sym = (call.get("yahoo_symbol") or "").upper()
    return (call.get("market") == "India"
            or call.get("currency") == "INR"
            or sym.endswith(".NS") or sym.endswith(".BO"))


def is_publishable(call, today):
    if not is_india(call):
        return True
    call_date = date.fromisoformat(call["call_date"])
    return call_date <= today - timedelta(days=INDIA_EMBARGO_DAYS)


def publishable(calls, today):
    return [c for c in calls if is_publishable(c, today)]


def build_summary(calls, updated):
    closed = [c for c in calls if c["status"] == "closed" and c.get("hit") is not None]
    hit_rate = round(100 * sum(1 for c in closed if c["hit"]) / len(closed), 1) if closed else None
    # Deprecated: raw alpha averaged over every call, blind to the call's direction.
    avg_alpha = round(sum(c["alpha"] for c in calls) / len(calls), 2) if calls else 0
    directional = [c for c in calls if c.get("direction", 0) != 0]
    holds = [c for c in calls if c.get("direction", 0) == 0]
    avg_signed = round(sum(c["signed_alpha"] for c in directional) / len(directional), 2) if directional else None
    right = sum(1 for c in directional if c["signed_alpha"] > 0)
    best = max(directional, key=lambda c: c["signed_alpha"]) if directional else None
    worst = min(directional, key=lambda c: c["signed_alpha"]) if directional else None
    hold_avg_abs = round(sum(abs(c["alpha"]) for c in holds) / len(holds), 2) if holds else None

    def brief(c):
        return {"company": c["company"], "rating": c["rating"], "call_date": c["call_date"],
                "alpha": c["alpha"], "signed_alpha": c["signed_alpha"]} if c else None

    return {
        "updated_at": updated,
        "total_calls": len(calls),
        "closed_calls": len(closed),
        "hit_rate_pct": hit_rate,
        "average_alpha_pct": avg_alpha,
        "directional_calls": len(directional),
        "avg_signed_alpha_pct": avg_signed,
        "directional_right": right,
        "hold_calls": len(holds),
        "hold_avg_abs_alpha_pct": hold_avg_abs,
        "india_embargo_days": INDIA_EMBARGO_DAYS,
        "best_call": brief(best),
        "worst_call": brief(worst),
    }


def main():
    today = datetime.now(timezone.utc).date()
    calls_path = os.path.join(DATA_DIR, "calls.json")
    with open(calls_path) as f:
        doc = json.load(f)
    before = len(doc.get("calls", []))
    doc["calls"] = publishable(doc.get("calls", []), today)
    with open(calls_path, "w") as f:
        json.dump(doc, f, indent=2)
    summary = build_summary(doc["calls"], doc.get("updated_at"))
    with open(os.path.join(DATA_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"publish: {len(doc['calls'])} of {before} calls publishable "
          f"(India calls younger than {INDIA_EMBARGO_DAYS} days withheld)")


if __name__ == "__main__":
    main()
