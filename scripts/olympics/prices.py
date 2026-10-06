"""Strict USD total-return prices. Raw closing prices are not a substitute."""
import math
from datetime import datetime, timezone


def parse(payload, ticker, today):
    chart = payload.get("chart") or {}
    rows = chart.get("result") or []
    if chart.get("error") or len(rows) != 1:
        raise ValueError(f"{ticker}: unavailable adjusted history")
    row = rows[0]
    meta = row.get("meta") or {}
    if meta.get("currency") != "USD" or meta.get("symbol", "").upper() != ticker.upper():
        raise ValueError(f"{ticker}: symbol/currency mismatch")
    adjusted = (row.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
    stamps = row.get("timestamp") or []
    if not adjusted or len(stamps) != len(adjusted):
        raise ValueError(f"{ticker}: adjusted prices missing")
    values = {}
    for stamp, price in zip(stamps, adjusted):
        day = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
        if day >= today:
            continue
        if price is None:
            continue  # Required held sessions are checked by the engine.
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ValueError(f"{ticker}: invalid adjusted price")
        values[day] = round(price, 6)
    if not values:
        raise ValueError(f"{ticker}: empty price history")
    splits = {}
    for event in row.get("events", {}).get("splits", {}).values():
        day = datetime.fromtimestamp(event["date"], timezone.utc).date().isoformat()
        n, d = float(event["numerator"]), float(event["denominator"])
        if n.is_integer() and d.is_integer() and n > 0 and d > 0:
            divisor = math.gcd(int(n), int(d))
            if max(int(n)//divisor, int(d)//divisor) <= 20 and n != d:
                splits[day] = n/d
    return {"ticker": ticker, "series": sorted(values.items()), "splits": splits}


def preserve(previous, incoming):
    old, new = dict(previous.get("series", [])), dict(incoming["series"])
    if old and (not set(old).issubset(new) or max(new) < max(old)):
        raise ValueError("adjusted history shrank; retaining old data")
    return incoming
