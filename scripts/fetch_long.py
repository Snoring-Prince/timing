"""
Daniel's timing — 장기 이력 (합친 차트용)

화면의 기간 버튼이 10Y·20Y·전체까지 늘어나면서, 5년치만 담는
data/market.json 으로는 모자라게 됐다. 이 스크립트가 받아 저장하는
data/market-long.json 이 그 긴 구간을 담당한다.

담는 것은 넷이다.
  spx — SPY (S&P 500 ETF)  1993년부터
  ndx — QQQ (나스닥 100 ETF) 1999년부터
  vix — VIX 변동성지수       1990년부터
  fng — CNN 공포탐욕지수      2011년부터

지수(SPX/NDX)가 아니라 ETF(SPY/QQQ)를 담는다. 백테스트가 이미 SPY·QQQ
기준이라, 화면의 낙폭은 지수·승률은 ETF 로 기준이 갈려 있었다. 여기서
맞춘다.

최근 DAILY_YEARS 년은 일봉, 그 이전은 주봉으로 줄인다. 20년 구간을
780px 폭에 그리면 1픽셀에 6.5일이 겹쳐서 일봉을 다 보내도 화면에는
드러나지 않는데 파일만 세 배가 된다. 주 단위로는 그 주의 마지막
거래일 종가를 쓴다.

주 1회(토요일)만 돌린다. 10년·20년 그래프가 며칠 늦는 것은 눈에 띄지
않고, 매일 큰 파일을 커밋하면 저장소가 무거워진다. 최근 구간은 지금처럼
market.json 이 매일 갱신한다.

저장 위치: scripts/fetch_long.py
"""

import csv
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = "data/market-long.json"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/csv,application/json,*/*",
}

# 1990-01-01. 야후는 range=max 를 주면 월봉으로 내려보내므로
# 일봉을 받으려면 period1/period2 를 명시해야 한다(backtest.py 와 같다).
SINCE = 631152000

# 이 기간만큼은 일봉 그대로 두고, 그 이전만 주봉으로 줄인다.
DAILY_YEARS = 5

# 공포탐욕지수 이력. 두 소스를 이어 붙여야 2011년까지 올라간다.
# 2020-09 ~ 2021-02 사이 약 4개월 공백이 있으나 화면에서는 선이 이어진다.
FNG_SOURCES = [
    ("2011-2020",
     "https://raw.githubusercontent.com/hackingthemarkets/"
     "sentiment-fear-and-greed/master/datasets/fear-greed.csv"),
    ("2021-현재",
     "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/"
     "main/datasets/cnn_fear_greed.csv"),
]

# key, 화면 이름(폴백용 — 사전이 우선), 야후 심볼, 소수점 자리
QUOTES = [
    ("spx", "S&P 500", "SPY", 2),
    ("ndx", "나스닥 100", "QQQ", 2),
    ("vix", "VIX", "^VIX", 2),
]


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:                        # noqa: BLE001
            last = e
            print(f"    재시도 {i + 1}/{tries}: {e}")
            time.sleep(4)
    raise last


# ------------------------------------------------------------ 데이터 수집

def yahoo_daily(symbol):
    """야후 일봉 종가(배당 반영). 지수에는 배당이 없으므로 VIX 도 같은 경로."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?period1={SINCE}&period2={int(time.time())}&interval=1d")
    j = json.loads(fetch(url))
    res = j["chart"]["result"][0]
    ind = res["indicators"]
    vals = None
    if ind.get("adjclose"):
        vals = ind["adjclose"][0].get("adjclose")
    if not vals:
        vals = ind["quote"][0]["close"]
    out = {}
    for t, c in zip(res["timestamp"], vals):
        if c is None:
            continue
        day = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
        out[day] = float(c)
    if len(out) < 1000:
        raise RuntimeError(f"{symbol}: 데이터 부족 ({len(out)}일)")
    return out


def load_fng():
    """두 소스를 병합. 겹치는 날짜는 나중 소스가 이긴다."""
    out = {}
    for label, url in FNG_SOURCES:
        try:
            raw = fetch(url).decode("utf-8", "replace")
        except Exception as e:                        # noqa: BLE001
            print(f"  {label} 실패: {e}")
            continue
        n = 0
        for r in csv.DictReader(io.StringIO(raw)):
            day = (r.get("Date") or "").strip()
            val = r.get("Fear Greed")
            if not day or val in (None, "", "NA"):
                continue
            try:
                out[day] = float(val)
                n += 1
            except ValueError:
                continue
        print(f"  {label}: {n}일")
    if len(out) < 500:
        raise RuntimeError(f"공포탐욕 데이터 부족 ({len(out)}일)")
    return out


# ------------------------------------------------------------ 솎아내기

def thin(points, daily_from, dec):
    """daily_from 이후는 그대로, 그 이전은 주 단위 마지막 거래일만 남긴다.

    points 는 {"YYYY-MM-DD": 값}. 반환은 날짜순 [[날짜, 값], ...].
    """
    keep = {}
    for day in points:
        if day >= daily_from:
            keep[day] = points[day]
            continue
        # ISO 주(월요일 시작)로 묶고, 그 주에서 가장 늦은 날만 남긴다
        y, w, _ = datetime.strptime(day, "%Y-%m-%d").date().isocalendar()
        cur = keep.setdefault(("w", y, w), day)
        if day > cur:
            keep[("w", y, w)] = day

    days = set()
    for k, v in keep.items():
        days.add(v if isinstance(k, tuple) else k)
    return [[d, round(points[d], dec) if dec else int(round(points[d]))]
            for d in sorted(days)]


def pack(key, name, points, daily_from, dec):
    ser = thin(points, daily_from, dec)
    if not ser:
        raise RuntimeError(f"{key}: 남은 행이 없다")
    weekly = sum(1 for d, _ in ser if d < daily_from)
    print(f"  {name:<10} {ser[0][0]} ~ {ser[-1][0]}  "
          f"{len(ser):,}행 (주봉 {weekly:,} + 일봉 {len(ser) - weekly:,})")
    return {"name": name, "from": ser[0][0], "to": ser[-1][0],
            "n": len(ser), "series": ser}


# ---------------------------------------------------------------- 실행

def main():
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
        except Exception as e:                        # noqa: BLE001
            print(f"기존 파일을 읽지 못함: {e}")
    old_series = (old.get("series") or {})

    daily_from = (datetime.now(timezone.utc)
                  - timedelta(days=365 * DAILY_YEARS)).strftime("%Y-%m-%d")
    print(f"일봉 유지 시작일: {daily_from}\n")

    series = {}
    failed = []

    for key, name, symbol, dec in QUOTES:
        print(f"[{name}] {symbol}")
        try:
            series[key] = pack(key, name, yahoo_daily(symbol), daily_from, dec)
            series[key]["ticker"] = symbol
        except Exception as e:                        # noqa: BLE001
            print(f"  실패: {e}")
            failed.append(name)
            # 한 소스가 막혀도 나머지는 갱신한다. 옛 값이라도 있는 편이 낫다.
            if key in old_series:
                series[key] = old_series[key]
                print("  → 기존 데이터 유지")

    print("\n[공포탐욕지수]")
    try:
        fng = pack("fng", "공포탐욕지수", load_fng(), daily_from, 0)
        fng["ticker"] = "CNN F&G"
        series["fng"] = fng
    except Exception as e:                            # noqa: BLE001
        print(f"  실패: {e}")
        failed.append("공포탐욕지수")
        if "fng" in old_series:
            series["fng"] = old_series["fng"]
            print("  → 기존 데이터 유지")

    if not series:
        raise SystemExit("모든 소스 실패 — 파일을 쓰지 않는다")

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dailyFrom": daily_from,
        "series": series,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(OUT)
    rows = sum(s["n"] for s in series.values())
    print(f"\n{OUT}  {size:,} bytes ({size / 1024:.0f} KB) · {rows:,}행")
    if failed:
        print(f"실패한 소스: {', '.join(failed)}")


if __name__ == "__main__":
    main()
