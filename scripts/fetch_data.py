"""
Daniel's timing — 데이터 수집 스크립트

S&P 500 / 나스닥 100 종가와 CNN 공포탐욕지수를 받아
data/market.json 하나로 저장한다. GitHub Actions가 매일 실행한다.

- 표준 라이브러리만 사용 (설치할 패키지 없음)
- 한쪽 출처가 실패해도 기존 데이터를 유지하고 계속 진행한다
"""

import csv
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = "data/market.json"
YEARS = 5  # 보관할 기간

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def fetch(url, tries=3):
    """재시도를 붙인 단순 GET."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:            # noqa: BLE001
            last = e
            print(f"  재시도 {i + 1}/{tries}: {e}")
            time.sleep(4)
    raise last


# ---------------------------------------------------------------- 지수

def stooq_history(symbol):
    """Stooq에서 일별 종가 전체 이력을 [(날짜, 종가)] 로 받아온다."""
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    text = fetch(url).decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for r in rows:
        d, c = r.get("Date"), r.get("Close")
        if not d or not c or c in ("N/A", "-"):
            continue
        try:
            out.append((d, float(c)))
        except ValueError:
            continue
    if len(out) < 100:
        raise RuntimeError(f"{symbol}: 데이터가 너무 적음 ({len(out)}행). "
                           "일시적 차단일 수 있음")
    out.sort()
    return out


def build_index(symbol, name, ticker):
    hist = stooq_history(symbol)
    peak_date, peak = max(hist, key=lambda kv: kv[1])   # 사상 최고 종가
    cur_date, cur = hist[-1]                            # 최신 종가
    cutoff = (datetime.strptime(cur_date, "%Y-%m-%d")
              - timedelta(days=365 * YEARS + 30)).strftime("%Y-%m-%d")
    series = [[d, round(v, 2)] for d, v in hist if d >= cutoff]
    print(f"  {ticker}: {len(series)}행, 현재 {cur:,.2f} ({cur_date}), "
          f"전고점 {peak:,.2f} ({peak_date})")
    return {
        "name": name,
        "ticker": ticker,
        "cur": round(cur, 2),
        "curDate": cur_date,
        "peak": round(peak, 2),
        "peakDate": peak_date,
        "series": series,
    }


# ---------------------------------------------------------- 공포탐욕지수

def build_fng(previous):
    """CNN에서 받아온 값을 기존 이력과 합친다."""
    start = (datetime.now(timezone.utc)
             - timedelta(days=365 * YEARS)).strftime("%Y-%m-%d")
    url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start}"
    payload = json.loads(fetch(url))
    points = payload["fear_and_greed_historical"]["data"]

    merged = {d: v for d, v in previous}          # 기존 이력
    for p in points:                              # 새로 받은 값으로 덮어쓰기
        day = datetime.fromtimestamp(
            p["x"] / 1000, timezone.utc).strftime("%Y-%m-%d")
        merged[day] = round(float(p["y"]))

    cutoff = (datetime.now(timezone.utc)
              - timedelta(days=365 * YEARS)).strftime("%Y-%m-%d")
    series = [[d, v] for d, v in sorted(merged.items()) if d >= cutoff]
    if not series:
        raise RuntimeError("공포탐욕지수 데이터가 비어 있음")

    print(f"  F&G: {len(series)}행, 현재 {series[-1][1]} ({series[-1][0]})")
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
        except Exception as e:                    # noqa: BLE001
            print(f"기존 파일을 읽지 못함: {e}")

    result = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "indices": dict(old.get("indices", {})),
        "fng": old.get("fng", {}),
    }
    failed = []

    for key, symbol, name, ticker in [
        ("spx", "^spx", "S&P 500", "SPX"),
        ("ndx", "^ndx", "나스닥 100", "NDX"),
    ]:
        print(f"{ticker} 받는 중…")
        try:
            result["indices"][key] = build_index(symbol, name, ticker)
        except Exception as e:                    # noqa: BLE001
            print(f"  실패: {e} — 기존 데이터를 유지합니다")
            failed.append(ticker)

    print("공포탐욕지수 받는 중…")
    try:
        result["fng"] = build_fng(old.get("fng", {}).get("series", []))
    except Exception as e:                        # noqa: BLE001
        print(f"  실패: {e} — 기존 데이터를 유지합니다")
        failed.append("F&G")

    if not result["indices"] or not result["fng"]:
        raise SystemExit("받아온 데이터가 하나도 없습니다. 중단합니다.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(OUT) / 1024
    print(f"\n저장 완료: {OUT} ({size:.0f}KB)")
    if failed:
        print(f"주의: {', '.join(failed)} 는 갱신하지 못했습니다.")


if __name__ == "__main__":
    main()
