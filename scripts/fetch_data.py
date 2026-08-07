"""
Daniel's timing — 데이터 수집 스크립트 (v2)

지수와 공포탐욕지수를 받아 data/market.json 하나로 저장한다.
GitHub Actions가 매일 실행한다. 표준 라이브러리만 사용한다.

출처를 하나만 믿지 않는다. 여러 곳을 순서대로 시도하고,
전부 실패하면 무엇이 어떻게 실패했는지 로그에 남긴다.
"""

import csv
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = "data/market.json"
YEARS = 5

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/csv,application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url, tries=2, pause=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:                       # noqa: BLE001
            last = e
            if i + 1 < tries:
                time.sleep(pause)
    raise last


def peek(raw, n=160):
    """실패 원인 파악용: 실제로 받은 내용의 앞부분."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    return " ".join(raw[:n].split())


# --------------------------------------------------------- 지수 출처들

def src_stooq(symbol):
    """Stooq CSV. ^ 는 반드시 %5E 로 인코딩해야 한다."""
    url = f"https://stooq.com/q/d/l/?s=%5E{symbol}&i=d"
    raw = fetch(url).decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(raw)))
    out = []
    for r in rows:
        try:
            out.append((r["Date"], float(r["Close"])))
        except (KeyError, TypeError, ValueError):
            continue
    if len(out) < 100:
        raise RuntimeError(f"CSV 아님 (받은 내용: {peek(raw)})")
    return out


def src_fred(series):
    """FRED 그래프 CSV. API 키가 필요 없는 경로."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    raw = fetch(url).decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        raise RuntimeError(f"빈 응답 ({peek(raw)})")
    out = []
    for r in rows[1:]:
        if len(r) < 2 or r[1] in (".", "", "NA"):
            continue
        try:
            out.append((r[0].strip(), float(r[1])))
        except ValueError:
            continue
    if len(out) < 100:
        raise RuntimeError(f"행이 부족 (받은 내용: {peek(raw)})")
    return out


def src_yahoo(symbol):
    """야후 차트 API."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/%5E{symbol}"
           "?range=10y&interval=1d")
    raw = fetch(url)
    j = json.loads(raw)
    res = j["chart"]["result"][0]
    stamps = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    out = []
    for t, c in zip(stamps, closes):
        if c is None:
            continue
        day = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
        out.append((day, float(c)))
    if len(out) < 100:
        raise RuntimeError("행이 부족")
    return out


# 지수별로 시도할 순서: (출처 이름, 함수, 그 출처에서 쓰는 기호)
INDEX_SOURCES = {
    "spx": [("Stooq", src_stooq, "spx"),
            ("FRED", src_fred, "SP500"),
            ("Yahoo", src_yahoo, "GSPC")],
    "ndx": [("Stooq", src_stooq, "ndx"),
            ("FRED", src_fred, "NASDAQ100"),
            ("Yahoo", src_yahoo, "NDX")],
}


def build_index(key, name, ticker):
    hist = None
    for label, fn, sym in INDEX_SOURCES[key]:
        try:
            hist = fn(sym)
            print(f"  {label} 성공 ({len(hist)}행)")
            break
        except Exception as e:                       # noqa: BLE001
            print(f"  {label} 실패: {e}")
    if not hist:
        raise RuntimeError("모든 출처 실패")

    hist = sorted(set(hist))
    peak_date, peak = max(hist, key=lambda kv: kv[1])
    cur_date, cur = hist[-1]
    cutoff = (datetime.strptime(cur_date, "%Y-%m-%d")
              - timedelta(days=365 * YEARS + 30)).strftime("%Y-%m-%d")
    dd = (cur / peak - 1) * 100
    print(f"  → 현재 {cur:,.2f} ({cur_date}) / "
          f"전고점 {peak:,.2f} ({peak_date}) / 낙폭 {dd:.2f}%")
    return {
        "name": name, "ticker": ticker,
        "cur": round(cur, 2), "curDate": cur_date,
        "peak": round(peak, 2), "peakDate": peak_date,
        "series": [[d, round(v, 2)] for d, v in hist if d >= cutoff],
    }


# --------------------------------------------------- 공포탐욕지수 출처들

MIRROR = ("https://raw.githubusercontent.com/whit3rabbit/fear-greed-data"
          "/main/json/cnn_output.json")


def _points(payload):
    data = payload["fear_and_greed_historical"]["data"]
    out = {}
    for p in data:
        day = datetime.fromtimestamp(
            p["x"] / 1000, timezone.utc).strftime("%Y-%m-%d")
        out[day] = round(float(p["y"]))
    return out


def src_fng_mirror():
    return _points(json.loads(fetch(MIRROR)))


def src_fng_cnn():
    start = (datetime.now(timezone.utc)
             - timedelta(days=365 * YEARS)).strftime("%Y-%m-%d")
    url = ("https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
           + start)
    return _points(json.loads(fetch(url)))


def build_fng(previous):
    merged = {d: v for d, v in previous}
    got = False
    for label, fn in [("GitHub 미러", src_fng_mirror), ("CNN 직접", src_fng_cnn)]:
        try:
            merged.update(fn())
            print(f"  {label} 성공")
            got = True
            break
        except Exception as e:                       # noqa: BLE001
            print(f"  {label} 실패: {e}")
    if not merged:
        raise RuntimeError("모든 출처 실패")
    if not got:
        print("  새로 받지 못해 기존 데이터만 사용")

    cutoff = (datetime.now(timezone.utc)
              - timedelta(days=365 * YEARS)).strftime("%Y-%m-%d")
    series = [[d, v] for d, v in sorted(merged.items()) if d >= cutoff]
    print(f"  → 현재 {series[-1][1]} ({series[-1][0]}), {len(series)}행")
    return {
        "value": series[-1][1],
        "date": series[-1][0],
        "prev": series[-2][1] if len(series) > 1 else series[-1][1],
        "series": series,
    }


# ---------------------------------------------------------------- 실행

def main():
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
        except Exception as e:                       # noqa: BLE001
            print(f"기존 파일을 읽지 못함: {e}")

    result = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "indices": dict(old.get("indices", {})),
        "fng": old.get("fng", {}),
    }
    failed = []

    for key, name, ticker in [("spx", "S&P 500", "SPX"),
                              ("ndx", "나스닥 100", "NDX")]:
        print(f"\n[{ticker}]")
        try:
            result["indices"][key] = build_index(key, name, ticker)
        except Exception as e:                       # noqa: BLE001
            print(f"  갱신 실패: {e}")
            failed.append(ticker)

    print("\n[공포탐욕지수]")
    try:
        result["fng"] = build_fng(old.get("fng", {}).get("series", []))
    except Exception as e:                           # noqa: BLE001
        print(f"  갱신 실패: {e}")
        failed.append("F&G")

    if not result["indices"] and not result["fng"]:
        raise SystemExit("\n받아온 데이터가 하나도 없습니다. 중단합니다.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n저장 완료: {OUT} ({os.path.getsize(OUT) / 1024:.0f}KB)")
    if failed:
        print(f"주의: {', '.join(failed)} 갱신 실패 (기존 값 유지)")


if __name__ == "__main__":
    main()
