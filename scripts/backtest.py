"""
Daniel's timing — 공포탐욕 지수값별 백테스팅

공포탐욕지수가 어떤 값이었던 날에 샀다면 1·3·6·12개월 뒤 어땠는지를
지수 0~100 한 눈금마다 집계해 data/backtest.json 에 저장한다.

구간을 다섯 덩어리로 묶으면 안 보이는 것이 있다. 예컨대 '극단적 공포'
한 칸에 지수 5와 24가 같이 들어가는데, 둘의 성적은 꽤 다르다.
그래서 눈금마다 ±WINDOW 포인트를 창으로 잡아 승률 곡선을 만든다.

기간 참고: CNN 공포탐욕지수는 2012년 봄에 나왔고, 구할 수 있는 값은
2011년까지 소급된 것이 가장 이르다. 그 이전은 어디에도 없으므로
백테스트 구간은 2011년 이후로 한정된다. 2008년 금융위기는 빠진다.

저장 위치: scripts/backtest.py
"""

import csv
import io
import json
import os
import statistics
import time
import urllib.request
from datetime import datetime, timezone

OUT = "data/backtest.json"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/csv,application/json,*/*",
}

# 공포탐욕지수 이력. 두 소스를 이어 붙여야 2011년까지 올라간다.
# 2020-09 ~ 2021-02 사이 약 4개월 공백이 있으나 통계에는 무해하다.
FNG_SOURCES = [
    ("2011-2020",
     "https://raw.githubusercontent.com/hackingthemarkets/"
     "sentiment-fear-and-greed/master/datasets/fear-greed.csv"),
    ("2021-현재",
     "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/"
     "main/datasets/cnn_fear_greed.csv"),
]

# 화면 배경의 색 띠에만 쓴다. 통계는 구간이 아니라 눈금마다 낸다.
ZONES = [
    ("extreme_fear", "극단적 공포", 0, 25),
    ("fear",         "공포",       25, 45),
    ("neutral",      "중립",       45, 55),
    ("greed",        "탐욕",       55, 75),
    ("extreme_greed", "극단적 탐욕", 75, 101),
]

# 보유 기간(거래일 기준). 월 21일, 분기 63일로 환산.
HORIZONS = [("1M", 21), ("3M", 63), ("6M", 126), ("1Y", 252)]

INDICES = [("spx", "S&P 500", "SPY"), ("ndx", "나스닥 100", "QQQ")]

# 눈금 v의 표본은 지수가 v-WINDOW ~ v+WINDOW 였던 날들이다.
# 좁히면 곡선이 톱니처럼 튀고, 넓히면 구간 평균과 다를 바 없어진다.
WINDOW = 5

# 표본이 이보다 적은 눈금은 비운다(화면에서 선이 끊긴다).
# 지수 97 이상처럼 역사적으로 며칠 없던 값은 숫자를 내봐야 오도한다.
MIN_N = 30


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


def load_prices(symbol):
    """배당 반영 종가를 쓴다. QQQ/SPY 모두 배당이 있어 총수익 기준이 맞다."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           "?range=20y&interval=1d")
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
        raise RuntimeError(f"{symbol}: 가격 데이터 부족 ({len(out)}일)")
    return out


# -------------------------------------------------------------- 집계

def backtest(fng, prices):
    """지수 눈금(0~100) × 보유기간별 승률 곡선을 만든다."""
    days = sorted(set(fng) & set(prices))
    if len(days) < 500:
        raise RuntimeError(f"겹치는 날짜 부족 ({len(days)}일)")

    px = [prices[d] for d in days]
    vals = [fng[d] for d in days]

    out = {}
    for hkey, span in HORIZONS:
        # 그 날 사서 span 거래일 뒤 팔았을 때의 수익률.
        # 아직 span 일이 안 지난 최근 날들은 결과가 없으므로 뺀다.
        pairs = [(vals[i], (px[i + span] / px[i] - 1) * 100)
                 for i in range(len(px) - span)]

        win, med, avg, ns = [], [], [], []
        for v in range(101):
            lo, hi = v - WINDOW, v + WINDOW
            rets = [r for f, r in pairs if lo <= f <= hi]
            n = len(rets)
            ns.append(n)
            if n < MIN_N:
                win.append(None)
                med.append(None)
                avg.append(None)
                continue
            wins = sum(1 for r in rets if r > 0)
            win.append(round(wins / n * 100, 1))
            # 화면에 그리는 선은 중앙값이다. 평균은 2020년 3월 바닥 같은
            # 며칠에 끌려가 공포 구간을 실제보다 후하게 보이게 만든다.
            med.append(round(statistics.median(rets), 2))
            avg.append(round(sum(rets) / n, 2))
        out[hkey] = {"win": win, "med": med, "avg": avg, "n": ns}
    return out, days


def main():
    print("공포탐욕지수 이력")
    fng = load_fng()
    fd = sorted(fng)
    print(f"  병합: {len(fng)}일 ({fd[0]} ~ {fd[-1]})")

    result = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": WINDOW,
        "min_n": MIN_N,
        "zones": [{"key": k, "label": l, "lo": lo, "hi": hi}
                  for k, l, lo, hi in ZONES],
        "horizons": [h for h, _ in HORIZONS],
        "indices": {},
    }

    for key, name, symbol in INDICES:
        print(f"\n{name} ({symbol})")
        try:
            prices = load_prices(symbol)
        except Exception as e:                        # noqa: BLE001
            print(f"  가격 실패: {e}")
            continue
        pd = sorted(prices)
        print(f"  가격: {len(prices)}일 ({pd[0]} ~ {pd[-1]})")
        curve, days = backtest(fng, prices)
        result["indices"][key] = {
            "name": name, "symbol": symbol,
            "from": days[0], "to": days[-1], "days": len(days),
            "curve": curve,
        }
        y = curve["1Y"]
        for v in range(0, 101, 10):
            w = y["win"][v]
            print(f"    지수 {v:3d}: 1년 중앙값 "
                  + (f"{y['med'][v]:+6.1f}% 평균 {y['avg'][v]:+6.1f}% "
                     f"승률 {w:5.1f}% (표본 {y['n'][v]})"
                     if w is not None else "  표본 부족"))

    if not result["indices"]:
        raise SystemExit("가격 데이터를 받지 못했습니다.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n저장 완료: {OUT} ({os.path.getsize(OUT) / 1024:.0f}KB)")


if __name__ == "__main__":
    main()
