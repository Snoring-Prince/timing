"""
Daniel's timing — 공포탐욕 구간별 백테스팅

공포탐욕지수가 특정 구간에 있던 날에 샀다면 1·3·6·12개월 뒤
어땠는지를 과거 데이터로 집계해 data/backtest.json 에 저장한다.

기간 참고: CNN 공포탐욕지수는 2011년부터 존재한다. 그 이전 값은
어디에도 없으므로 백테스트 구간은 2011년 이후로 한정된다.

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

# 화면에 쓰는 것과 같은 구간 정의
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

# 표본이 이보다 적은 칸은 통계로 쓰지 않고 비운다.
# 1M·3M 같은 단기 구간은 거시 이슈 하나에 통째로 휘둘리므로,
# 표본이 얇으면 숫자가 있는 편이 오히려 사람을 오도한다.
MIN_N = 20


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

def summarize(returns):
    """수익률 목록을 요약. 평균은 이상치에 약해 중앙값도 함께 낸다."""
    n = len(returns)
    wins = sum(1 for r in returns if r > 0)
    return {
        "n": n,
        "win": round(wins / n * 100, 1),
        "avg": round(sum(returns) / n, 2),
        "med": round(statistics.median(returns), 2),
        "best": round(max(returns), 2),
        "worst": round(min(returns), 2),
    }


def backtest(fng, prices):
    """구간 × 보유기간별 결과를 만든다."""
    days = sorted(set(fng) & set(prices))
    if len(days) < 500:
        raise RuntimeError(f"겹치는 날짜 부족 ({len(days)}일)")

    idx = {d: i for i, d in enumerate(days)}
    px = [prices[d] for d in days]

    out = {}
    for key, _, lo, hi in ZONES:
        entries = [d for d in days if lo <= fng[d] < hi]
        out[key] = {}
        for hkey, span in HORIZONS:
            rets = []
            for d in entries:
                i = idx[d]
                j = i + span
                if j >= len(px):          # 아직 결과가 안 나온 날은 제외
                    continue
                rets.append((px[j] / px[i] - 1) * 100)
            out[key][hkey] = summarize(rets) if len(rets) >= MIN_N else None
    return out, days


def main():
    print("공포탐욕지수 이력")
    fng = load_fng()
    fd = sorted(fng)
    print(f"  병합: {len(fng)}일 ({fd[0]} ~ {fd[-1]})")

    result = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        stats, days = backtest(fng, prices)
        result["indices"][key] = {
            "name": name, "symbol": symbol,
            "from": days[0], "to": days[-1], "days": len(days),
            "stats": stats,
        }
        for zk, _, lo, hi in ZONES:
            row = stats[zk].get("1Y")
            if row:
                print(f"    {lo}~{hi}: 1년 승률 {row['win']}% "
                      f"평균 {row['avg']:+.1f}% (표본 {row['n']})")

    if not result["indices"]:
        raise SystemExit("가격 데이터를 받지 못했습니다.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n저장 완료: {OUT} ({os.path.getsize(OUT) / 1024:.0f}KB)")


if __name__ == "__main__":
    main()
