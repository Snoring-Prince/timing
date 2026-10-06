"""Samuel's daily adjusted prices. Export before chart history is thinned.

Reuses the two equity histories and adds BIL to the weekly job. An incomplete
export preserves the last complete file and fails the job so Telegram can notify.
"""
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data/samuel/prices.json"
SYMBOLS = {"spx": "SPY", "ndx": "QQQ", "reserve": "BIL"}


def publish(quotes, output=OUT, today=None):
    today = today or datetime.now(timezone.utc).date()
    packed = {}
    for key, symbol in SYMBOLS.items():
        rows = []
        for day, value in sorted(quotes.get(key, {}).items()):
            parsed = date.fromisoformat(day)
            if parsed >= today:  # Do not publish a possibly unfinished session.
                continue
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{symbol}: invalid adjusted price on {day}")
            rows.append([day, round(value, 6)])
        if len(rows) < 1000:
            raise ValueError(f"{symbol}: incomplete daily history ({len(rows)})")
        if (today-date.fromisoformat(rows[-1][0])).days > 10:
            raise ValueError(f"{symbol}: latest daily price is stale")
        if any((date.fromisoformat(b[0])-date.fromisoformat(a[0])).days > 10 for a, b in zip(rows, rows[1:])):
            raise ValueError(f"{symbol}: daily history has a long gap")
        packed[key] = {"ticker": symbol, "from": rows[0][0], "to": rows[-1][0], "series": rows}
    output = Path(output)
    reserve_days = {row[0] for row in packed["reserve"]["series"]}
    for key in ("spx", "ndx"):
        start = max(packed[key]["from"], packed["reserve"]["from"])
        end = min(packed[key]["to"], packed["reserve"]["to"])
        if any(start <= row[0] <= end and row[0] not in reserve_days for row in packed[key]["series"]):
            raise ValueError(f"{key}: BIL session missing inside shared history")
    payload = {"version": 2, "basis": "dividend-adjusted", "frequency": "daily", "series": packed}
    # A shorter response must not silently remove older history or roll back its end.
    if output.exists():
        old = json.loads(output.read_text(encoding="utf-8"))
        for key in SYMBOLS:
            previous = old.get("series", {}).get(key, {})
            if previous and (packed[key]["from"] > previous["from"] or packed[key]["to"] < previous["to"]):
                raise ValueError(f"{key}: collected range shrank; keeping previous file")
            if previous and not {row[0] for row in previous["series"]}.issubset({row[0] for row in packed[key]["series"]}):
                raise ValueError(f"{key}: previously stored sessions are missing; keeping previous file")
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n"
    if output.exists() and output.read_text(encoding="utf-8") == encoded:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, output)
    return True


if __name__ == "__main__":
    # One-time bootstrap only; the normal scheduled run passes its existing data.
    from fetch_long import yahoo_daily
    publish({key: yahoo_daily(symbol) for key, symbol in SYMBOLS.items()})
