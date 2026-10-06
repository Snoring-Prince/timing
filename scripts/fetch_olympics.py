"""Weekly self-contained race data, with immutable public-date disclosures.

All inputs must succeed before replacing the published race. Failures keep the
last complete race and fail the workflow for the existing Telegram notifier.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import fetch_13f as sec
import fetch_prices as ticker_source
from fetch_long import fetch, load_fng
from olympics.filings import collect, timeline, candidates
from olympics.prices import parse, preserve
from olympics.identities import baseline_aliases

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/olympics"
START = "2025-01-01"


def read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def build(folder=OUT):
    today = datetime.now(timezone.utc).date().isoformat()
    saved = read(folder / "filings.json", {"disclosures": [], "symbols": {}})
    book = read(ROOT / "data/titans/berkshire.json", {})
    sec.configure("berkshire")
    contact = os.environ.get("SEC_CONTACT") or "https://itpaidoff.com"

    def reader(acc, filed):
        doc, bad = sec.one_doc(acc, contact, filed)
        if bad:
            raise ValueError(f"{acc}: {bad}")
        total = sum(r["value"] for r in doc["rows"])
        if doc["total"] is not None and total != doc["total"]:
            raise ValueError(f"{acc}: SEC cover total mismatch")
        return sec.fold(doc["rows"], 1), doc["amend"]["type"]

    disclosures = collect(book, saved["disclosures"], reader,
                          lambda: sum(sec.list_filings(contact), []))
    required = {h["cusip"]: h for d in disclosures for h in d["holdings"]}
    cache = read(ROOT / "data/titans/prices.json", {"series": {}})["series"]
    symbols = dict(saved["symbols"])
    symbols.update(baseline_aliases(required))
    for cusip in required:
        if cusip not in symbols and cache.get(cusip, {}).get("ticker"):
            symbols[cusip] = cache[cusip]["ticker"]
    missing = sorted(set(required) - set(symbols))
    if missing:
        symbols.update(ticker_source.resolve(missing, required,
                       read(ROOT / "data/titans/tickers.json", {})))
    if set(required) - set(symbols):
        raise ValueError(f"Unresolved share classes: {sorted(set(required)-set(symbols))}")
    events = timeline(disclosures, symbols)
    old_stocks = read(folder / "stocks.json", {})
    stocks = {}
    for ticker in sorted(candidates(events)):
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}"
               f"?period1=1727740800&period2={int(time.time())}&interval=1d&events=splits")
        incoming = parse(json.loads(fetch(url)), ticker, today)
        stocks[ticker] = preserve(old_stocks.get(ticker, {}), incoming)
        print(f"{ticker}: {len(stocks[ticker]['series'])} adjusted sessions", flush=True)
        time.sleep(.25)
    etfs = read(ROOT / "data/samuel/prices.json", {})
    if etfs.get("version") != 2 or etfs.get("basis") != "dividend-adjusted":
        raise ValueError("Samuel adjusted ETF data unavailable")
    packed = {k: [r for r in etfs["series"][k]["series"] if r[0] >= START]
              for k in ("spx", "ndx", "reserve")}
    end = min(rows[-1][0] for rows in packed.values())
    if (datetime.fromisoformat(today)-datetime.fromisoformat(end)).days > 10:
        raise ValueError("ETF history stale")
    fear = [[d, v] for d, v in sorted(load_fng().items()) if START <= d <= end]
    if not fear or (datetime.fromisoformat(end)-datetime.fromisoformat(fear[-1][0])).days > 10:
        raise ValueError("Fear & Greed history stale")
    if any(not isinstance(v, (int, float)) or not 0 <= v <= 100 for _, v in fear):
        raise ValueError("Invalid Fear & Greed value")
    payload = {"version": 1, "basis": "dividend-adjusted", "from": max(rows[0][0] for rows in packed.values()),
               "to": end, "etfs": packed, "fear": fear, "disclosures": events, "stocks": stocks}
    old = read(folder / "race.json", {})
    if old and (payload["from"] > old["from"] or end < old["to"]):
        raise ValueError("Race range shrank")
    # Execute the same engine used by visitors before publishing. No fake prices.
    import subprocess
    node = os.environ.get("NODE_BINARY") or "node"
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    subprocess.run([node, str(ROOT / "olympics/validate.cjs")], input=encoded,
                   text=True, encoding="utf-8", check=True)
    return {"filings.json": {"disclosures": disclosures, "symbols": symbols},
            "stocks.json": stocks, "race.json": payload}


def publish(folder, files):
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = folder / name
        encoded = json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"
        if target.exists() and target.read_text(encoding="utf-8") == encoded:
            continue
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(encoded, encoding="utf-8")
        os.replace(tmp, target)


if __name__ == "__main__":
    try:
        publish(OUT, build())
    except Exception as exc:
        print(f"Investment race failed; previous complete data retained: {exc}", file=sys.stderr)
        sys.exit(1)
