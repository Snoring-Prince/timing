"""
Daniel's timing — 지수값별 백테스팅 (공포탐욕 / VIX)

"시장이 이만큼 겁먹었던 날 샀다면 1·3·6·12개월 뒤 어땠나"를
잣대 눈금마다 집계해 data/backtest.json 에 저장한다.

잣대는 둘이다.
  fng — CNN 공포탐욕지수 0~100. 낮을수록 공포. 2011년부터.
  vix — VIX 변동성지수. 높을수록 공포. 1990년부터.

VIX를 함께 두는 이유는 표본이다. 공포탐욕은 2011년부터라 2008년
금융위기가 통째로 빠지고, 남은 기간이 거의 강세장이라 구간별 차이가
잘 드러나지 않는다. VIX는 1990년부터 있어 닷컴과 리먼이 들어온다.

구간을 몇 덩어리로 묶지 않고 눈금마다 ±WINDOW 만큼을 창으로 잡는다.
'극단적 공포' 한 칸에 지수 5와 24를 같이 넣으면 성적이 뭉개진다.

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

# 1990-01-01. 야후는 range=max 를 주면 월봉으로 내려보내므로
# 일봉을 받으려면 period1/period2 를 명시해야 한다.
SINCE = 631152000

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

# 보유 기간(거래일 기준). 위 지수 패널의 기간 버튼과 같은 눈금을 쓴다.
# 달력일을 거래일로 환산: 한 해 252거래일 기준.
HORIZONS = [("30D", 21), ("90D", 63), ("180D", 126),
            ("1Y", 252), ("3Y", 756), ("5Y", 1260)]

INDICES = [("spx", "S&P 500", "SPY"), ("ndx", "나스닥 100", "QQQ")]

# 표본이 이보다 적은 눈금은 비운다(화면에서 선이 끊긴다).
MIN_N = 30

# 두 잣대의 정의. tone 은 배경 색 띠 — 음수가 공포(파랑), 양수가 탐욕(빨강).
# lo/hi 는 화면에 보여줄 가로축 범위이고, 통계는 0~100 눈금 전부에 대해 낸다.
AXES = [
    {
        "key": "fng",
        "label": "공포탐욕지수",
        "short": "공포탐욕",
        "title": "공포와 탐욕 지수별 수익률",
        "window": 5,
        "lo": 0, "hi": 100, "step": 25, "dec": 0,
        "zones": [("극단적 공포", 0, 25, -2), ("공포", 25, 45, -1),
                  ("중립", 45, 55, 0), ("탐욕", 55, 75, 1),
                  ("극단적 탐욕", 75, 101, 2)],
        "help": ("공포탐욕지수는 CNN이 시장 분위기를 0~100 한 숫자로 나타낸 것입니다. "
                 "0에 가까울수록 다들 겁먹은 상태, 100에 가까울수록 들뜬 상태입니다. "
                 "왼쪽이 공포입니다."),
    },
    {
        "key": "vix",
        "label": "VIX",
        "short": "VIX",
        "title": "VIX별 수익률",
        "window": 1.5,
        "lo": 10, "hi": 45, "step": 5, "dec": 1,
        # 구간 경계는 1990년 이후 VIX 분포의 백분위에 맞춰 잡았다.
        # 처음엔 15/20/28/40 이라는 둥근 숫자를 썼는데, 백분위로 보니
        # 20이 겨우 중간(63%)인데도 '불안'이라 부르고 있었다.
        # 13→하위15%, 17→45%, 22→72%, 30→92%, 40→98%.
        "zones": [("아주 잠잠", 0, 13, 2), ("잠잠", 13, 17, 1),
                  ("보통", 17, 22, 0), ("불안", 22, 30, -1),
                  ("공포", 30, 40, -2), ("패닉", 40, 200, -2)],
        "help": ("VIX는 앞으로 한 달 주가가 얼마나 출렁일지 시장이 내다보는 정도라서 "
                 "'공포지수'라고 부릅니다. 1990년 이후 절반이 17.6 아래였고, "
                 "22를 넘은 날은 넷 중 하나뿐입니다. 30을 넘으면 상위 8%, "
                 "40을 넘으면 상위 2%의 드문 공포입니다. "
                 "공포탐욕지수와 반대로 오른쪽이 공포입니다."),
    },
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
    """야후 일봉 종가(배당 반영). period1/period2 로 전 기간을 받는다."""
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


# -------------------------------------------------------------- 집계

def backtest(gauge, prices, window):
    """잣대 눈금(0~100) × 보유기간별 수익률과 승률."""
    days = sorted(set(gauge) & set(prices))
    if len(days) < 500:
        raise RuntimeError(f"겹치는 날짜 부족 ({len(days)}일)")

    px = [prices[d] for d in days]
    vals = [gauge[d] for d in days]

    out = {}
    for hkey, span in HORIZONS:
        # 그 날 사서 span 거래일 뒤 팔았을 때의 수익률.
        # 아직 span 일이 안 지난 최근 날들은 결과가 없으므로 뺀다.
        pairs = [(vals[i], (px[i + span] / px[i] - 1) * 100)
                 for i in range(len(px) - span)]

        win, med, avg, ns = [], [], [], []
        for v in range(101):
            lo, hi = v - window, v + window
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
    gauges = {}

    print("[공포탐욕지수]")
    try:
        fng = load_fng()
        fd = sorted(fng)
        print(f"  병합: {len(fng)}일 ({fd[0]} ~ {fd[-1]})")
        gauges["fng"] = fng
    except Exception as e:                            # noqa: BLE001
        print(f"  실패: {e}")

    print("\n[VIX]")
    try:
        vix = yahoo_daily("%5EVIX")
        vd = sorted(vix)
        print(f"  {len(vix)}일 ({vd[0]} ~ {vd[-1]})")
        gauges["vix"] = vix
    except Exception as e:                            # noqa: BLE001
        print(f"  실패: {e}")

    if not gauges:
        raise SystemExit("잣대를 하나도 받지 못했습니다.")

    result = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "min_n": MIN_N,
        "axes": [{**{k: a[k] for k in
                     ("key", "label", "short", "title", "window",
                      "lo", "hi", "step", "dec", "help")},
                  "zones": [{"label": l, "lo": lo, "hi": hi, "tone": t}
                            for l, lo, hi, t in a["zones"]]}
                 for a in AXES if a["key"] in gauges],
        "horizons": [h for h, _ in HORIZONS],
        "indices": {},
    }

    for key, name, symbol in INDICES:
        print(f"\n[{name} ({symbol})]")
        try:
            prices = yahoo_daily(symbol)
        except Exception as e:                        # noqa: BLE001
            print(f"  가격 실패: {e}")
            continue
        pd = sorted(prices)
        print(f"  가격: {len(prices)}일 ({pd[0]} ~ {pd[-1]})")

        curve = {}
        for a in AXES:
            if a["key"] not in gauges:
                continue
            try:
                h, days = backtest(gauges[a["key"]], prices, a["window"])
            except Exception as e:                    # noqa: BLE001
                print(f"  {a['label']} 집계 실패: {e}")
                continue
            curve[a["key"]] = {"from": days[0], "to": days[-1],
                               "days": len(days), "h": h}
            y = h["1Y"]
            span = a["hi"] - a["lo"]
            print(f"  {a['label']} — {days[0]}~{days[-1]} ({len(days)}일), 1년 보유")
            for k in range(6):
                v = int(round(a["lo"] + span * k / 5))
                w = y["win"][v]
                print(f"    {a['short']} {v:3d}: "
                      + (f"중앙값 {y['med'][v]:+6.2f}%  승률 {w:5.1f}%  "
                         f"(표본 {y['n'][v]})"
                         if w is not None else "표본 부족"))
        if curve:
            result["indices"][key] = {"name": name, "symbol": symbol,
                                      "curve": curve}

    if not result["indices"]:
        raise SystemExit("가격 데이터를 받지 못했습니다.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n저장 완료: {OUT} ({os.path.getsize(OUT) / 1024:.0f}KB)")


if __name__ == "__main__":
    main()
