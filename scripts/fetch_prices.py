#!/usr/bin/env python3
"""Shared daily closing-price cache for all 13F books; no visitor-side provider calls.

Yahoo quote.close is split-adjusted, not dividend-adjusted. The public chart
endpoint is unofficial; accessibility does not establish redistribution rights.
OpenFIGI resolves exact CUSIPs (logo name matching is unsuitable for prices).
"""
import argparse
import datetime as dt
import json
import math
import os
import re
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
from fetch_tickers import norm

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/titans/prices.json"
UTC = dt.timezone.utc
NY = ZoneInfo("America/New_York")


def from_epoch(stamp):
    # Windows fromtimestamp() rejects some pre-1970 IPO timestamps.
    return dt.datetime(1970, 1, 1, tzinfo=UTC)+dt.timedelta(seconds=stamp)


def years_before(day, years=15):
    try:
        return day.replace(year=day.year-years)
    except ValueError:
        return day.replace(year=day.year-years, day=28)


def request(url, payload=None):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=40) as res:
                return json.load(res)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(5*(attempt+1))


def required_cusips(books):
    """Cache every current share class; a new investor reuses the same CUSIP."""
    required = {}
    for book in books:
        quarters = book.get("quarters", [])
        if not quarters:
            continue
        latest = max(quarters, key=lambda q: q["period"])
        for h in latest["holdings"]:
            if h.get("shares", 0) > 0 and h.get("value", 0) > 0:
                required[h["cusip"]] = {"name": h["name"], "class": h.get("class", "")}
    return required


def resolve(cusips, required, known):
    result = {}
    for offset in range(0, len(cusips), 10):
        batch = cusips[offset:offset+10]
        rows = request("https://api.openfigi.com/v3/mapping", [
            {"idType": "ID_CUSIP", "idValue": c, "exchCode": "US"} for c in batch])
        if not isinstance(rows, list) or len(rows) != len(batch):
            raise ValueError("OpenFIGI response size mismatch")
        for c, row in zip(batch, rows):
            candidates = {r["ticker"] for r in row.get("data", [])
                          if r.get("marketSector") == "Equity" and r.get("exchCode") == "US" and r.get("ticker")}
            if len(candidates) == 1:
                result[c] = candidates.pop().replace("/", "-").replace(".", "-")
        if offset+10 < len(cusips):
            time.sleep(3)
    # CINS mapping is absent for some foreign issuers. An old logo ticker is
    # usable only for the sole plain common class and a verified US common-stock
    # issuer match. Never apply this fallback to A/B/C, preferred or ADR classes.
    for cusip in cusips:
        identity = required[cusip]
        issuer_classes = [c for c in required if c[:6] == cusip[:6]]
        if cusip in result or cusip[0].isdigit() or len(issuer_classes) != 1 or not re.fullmatch(r"COM(?:MON(?: STOCK)?)?", identity["class"].upper().strip()):
            continue
        ticker = known.get(cusip)
        if not ticker:
            continue
        rows = request("https://api.openfigi.com/v3/mapping", [
            {"idType": "TICKER", "idValue": ticker, "exchCode": "US"}])
        candidates = [r for r in rows[0].get("data", []) if r.get("ticker") == ticker
                      and r.get("securityType") == "Common Stock"
                      and sorted(norm(r.get("name", ""))) == sorted(norm(identity["name"]))]
        if candidates and len({r.get("shareClassFIGI") for r in candidates}) == 1:
            result[cusip] = ticker
    return result


def parse_chart(payload, ticker, now):
    result = payload.get("chart", {}).get("result")
    if not result or payload["chart"].get("error"):
        raise ValueError(f"{ticker}: missing chart")
    row = result[0]
    meta = row["meta"]
    if meta.get("currency") != "USD" or meta.get("symbol", "").upper() != ticker.upper():
        raise ValueError(f"{ticker}: symbol/currency mismatch")
    stamps = row.get("timestamp", [])
    closes = row["indicators"]["quote"][0]["close"]
    if len(stamps) != len(closes):
        raise ValueError(f"{ticker}: unequal timestamps/prices")
    # Current day's chart bar may still be an intraday last price. Wait until 20:00 ET.
    local = now.astimezone(NY)
    cutoff = local.date() if local.hour >= 20 else local.date()-dt.timedelta(days=1)
    values = {}
    for stamp, close in zip(stamps, closes):
        day = from_epoch(stamp).astimezone(NY).date()
        if day <= cutoff and isinstance(close, (int, float)) and not isinstance(close, bool) and math.isfinite(close) and close > 0:
            values[day.isoformat()] = round(close, 4)
    splits = {from_epoch(int(v["date"])).astimezone(NY).date().isoformat():
              f"{v['numerator']}:{v['denominator']}"
              for v in row.get("events", {}).get("splits", {}).values()}
    if not values:
        raise ValueError(f"{ticker}: no completed closing prices")
    return sorted(values.items()), splits


def merge_series(old, values, splits, start, full):
    """Never replace 15 years with a short response, or combine split bases."""
    if old and old.get("splits", {}) != splits and not full:
        raise ValueError("split basis changed: full refresh required")
    previous = dict(old.get("values", [])) if old else {}
    incoming = dict(values)
    if full and previous:
        if max(incoming) < max(previous):
            raise ValueError("full refresh would remove newer saved closing prices")
        expected = [day for day in previous if day >= start and day <= max(incoming)]
        if len(incoming) < len(expected)*.98:
            raise ValueError("full refresh is unexpectedly shorter than saved history")
    merged = incoming if full else previous | incoming
    return {"values": [[day, merged[day]] for day in sorted(merged) if day >= start], "splits": splits}


def collect(required, previous, now, full=False, known=None):
    saved = previous.get("series", {})
    # Weekly/full verification also catches ticker changes of the same security.
    missing = [c for c in required if full or now.weekday() == 5 or not saved.get(c, {}).get("ticker")]
    series = dict(saved)
    errors = []
    try:
        mapped = resolve(missing, required, known or {}) if missing else {}
    except Exception as exc:
        mapped = {}
        errors.append(f"ticker mapping unavailable: {exc}")
    start = years_before(now.astimezone(NY).date())-dt.timedelta(days=7)
    for cusip, identity in sorted(required.items()):
        old = saved.get(cusip, {})
        ticker = mapped.get(cusip) or old.get("ticker")
        try:
            if not ticker:
                raise ValueError("exact CUSIP mapping unavailable")
            refresh = full or not old.get("values") or now.weekday() == 5
            first = start if refresh else dt.date.fromisoformat(old["values"][-1][0])-dt.timedelta(days=10)
            def download(day):
                p1 = int(dt.datetime.combine(day, dt.time(), NY).timestamp())
                url = ("https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(ticker, safe="")+
                       f"?period1={p1}&period2={int(now.timestamp())}&interval=1d&events=splits")
                payload = request(url)
                parsed = parse_chart(payload, ticker, now)
                first_trade = payload["chart"]["result"][0]["meta"].get("firstTradeDate")
                if day == start and first_trade:
                    expected = max(start, from_epoch(first_trade).astimezone(NY).date())
                    if dt.date.fromisoformat(parsed[0][0][0]) > expected+dt.timedelta(days=14):
                        raise ValueError("response starts too late for a full history")
                    elapsed = (dt.date.fromisoformat(parsed[0][-1][0])-expected).days
                    if len(parsed[0]) < elapsed/365.25*252*.75:
                        raise ValueError("full history has unexpectedly few daily prices")
                return parsed
            values, splits = download(first)
            # Incremental responses only contain recent split events. Compare those;
            # a newly reported or changed event forces an entire history download.
            if not refresh:
                if any(old.get("splits", {}).get(day) != ratio for day, ratio in splits.items()):
                    refresh = True
                    values, splits = download(start)
                else:
                    splits = old.get("splits", {}) | splits
            if (now.astimezone(NY).date()-dt.date.fromisoformat(values[-1][0])).days > 7:
                raise ValueError("last closing price is more than seven days old")
            series[cusip] = {**identity, "ticker": ticker, "currency": "USD",
                            **merge_series(old, values, splits, start.isoformat(), refresh)}
            print(f"{cusip} {ticker}: {len(series[cusip]['values'])} days, last {series[cusip]['values'][-1][0]}", flush=True)
        except Exception as exc:
            errors.append(f"{cusip} {ticker or '?'}: {exc}")
        time.sleep(.3)
    result = {"method": "split-adjusted-close", "series": series}
    return result, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    books = [json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "data/titans").glob("*.json")]
    required = required_cusips(books)
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    known = json.loads((ROOT / "data/titans/tickers.json").read_text(encoding="utf-8"))
    result, errors = collect(required, previous, dt.datetime.now(UTC), args.full, known)
    if result["series"] != previous.get("series", {}):
        tmp = OUT.with_suffix(".tmp")
        tmp.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"))+"\n", encoding="utf-8")
        os.replace(tmp, OUT)
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
