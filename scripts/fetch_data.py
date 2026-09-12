"""
Daniel's timing — 데이터 수집 스크립트 (v3)

SPY·QQQ·공포탐욕지수·VIX를 받아 data/market.json 하나로 저장한다.
화면은 이 파일에서 (1) 갱신 시각 (2) 공포탐욕·VIX 현재값 (3) 위 차트의
최근 며칠치를 가져간다. 긴 이력은 market-long.json 이 주 1회 따로 받는다.
GitHub Actions가 매일 실행한다. 표준 라이브러리만 사용한다.

출처를 하나만 믿지 않는다. 여러 곳을 순서대로 시도하고,
전부 실패하면 무엇이 어떻게 실패했는지 로그에 남긴다.

저장 위치: scripts/fetch_data.py
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


def src_yahoo(symbol):
    """야후 차트 API. 심볼은 받은 그대로 쓴다 — 지수는 `%5E` 를 붙여 넘긴다.

    ETF 는 분배금을 지급하면 그만큼 가격이 떨어지므로(배당락) 종가 대신
    배당 반영가(adjclose)를 쓴다. fetch_long.py 가 같은 기준이라,
    화면에서 두 파일을 이어 붙여도 이음매에서 값이 튀지 않는다.
    """
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           "?range=10y&interval=1d")
    j = json.loads(fetch(url))
    res = j["chart"]["result"][0]
    stamps = res["timestamp"]
    ind = res["indicators"]
    closes = None
    if ind.get("adjclose"):
        closes = ind["adjclose"][0].get("adjclose")
    if not closes:
        closes = ind["quote"][0]["close"]
    out = []
    for t, c in zip(stamps, closes):
        if c is None:
            continue
        day = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
        out.append((day, float(c)))
    if len(out) < 100:
        raise RuntimeError("행이 부족")
    return out


# 지수가 아니라 ETF 를 받는다 (2026-09-12).
#
# 화면의 위 차트는 market-long.json 이 그리는데 그 파일은 주 1회만 갱신된다.
# 그래서 금요일 종가가 다음 토요일까지 화면에 안 나왔다 — 최대 6일이 밀렸다.
# 이 파일은 매일 갱신되므로 화면이 뒤쪽 며칠을 여기서 이어 붙이면 해결되는데,
# 예전에는 이 파일이 지수(SPX 7,656)를 담고 저 파일이 ETF(SPY 765.96)를 담아
# 기준이 서로 달라서 이어 붙일 수가 없었다. 여기서 기준을 맞춘다.
#
# 그 대신 Stooq·FRED 는 빠졌다. 둘 다 지수만 주지 SPY·QQQ 를 주지 않는다.
# (Stooq 의 spy.us 는 배당 미반영이라 이어 붙이면 이음매가 생긴다.)
# 야후가 실패하면 아래 main() 이 기존 값을 그대로 유지한다.
QUOTE_SOURCES = {
    "spx": [("Yahoo", src_yahoo, "SPY")],
    "ndx": [("Yahoo", src_yahoo, "QQQ")],
}


def build_index(key, name, ticker):
    hist = None
    for label, fn, sym in QUOTE_SOURCES[key]:
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


# ------------------------------------------------------------------ VIX

# 승률 차트의 두 번째 가로축이자 위 게이지 차트의 두 번째 잣대.
# 게이지가 공포탐욕과 같은 방식으로 이력을 그리므로 fng 와 같은 5년치를 담는다
# (구간별 통계는 backtest.py 가 따로 20년치를 받아 계산한다).

def build_vix():
    hist = None
    for label, fn, sym in [("Stooq", src_stooq, "vix"),
                           ("Yahoo", src_yahoo, "%5EVIX")]:
        try:
            hist = fn(sym)
            print(f"  {label} 성공 ({len(hist)}행)")
            break
        except Exception as e:                       # noqa: BLE001
            print(f"  {label} 실패: {e}")
    if not hist:
        raise RuntimeError("모든 출처 실패")

    hist = sorted(set(hist))
    cur_date, cur = hist[-1]
    prev = hist[-2][1] if len(hist) > 1 else cur

    cutoff = (datetime.now(timezone.utc)
              - timedelta(days=365 * YEARS)).strftime("%Y-%m-%d")
    series = [[d, round(v, 2)] for d, v in hist if d >= cutoff]
    print(f"  → 현재 {cur:.2f} ({cur_date}), 전일 {prev:.2f}, {len(series)}행")
    return {
        "value": round(cur, 2),
        "date": cur_date,
        "prev": round(prev, 2),
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
        "vix": old.get("vix", {}),
    }
    failed = []

    # ticker 는 화면이 "이어 붙여도 되는 파일인가"를 판단하는 표식이기도 하다.
    # market-long.json 의 ticker 와 같을 때만 이어 붙인다.
    for key, name, ticker in [("spx", "S&P 500", "SPY"),
                              ("ndx", "나스닥 100", "QQQ")]:
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

    print("\n[VIX]")
    try:
        result["vix"] = build_vix()
    except Exception as e:                           # noqa: BLE001
        print(f"  갱신 실패: {e}")
        failed.append("VIX")

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
