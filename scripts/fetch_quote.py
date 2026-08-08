"""
Daniel's timing — 장중 시세 수집

두 지수의 현재가만 아주 작은 JSON으로 만들어 표준출력에 뱉는다.
결과는 별도 브랜치(data)에 올라가므로 Pages 빌드를 건드리지 않는다.

원천이 실제로 몇 분 지연인지 눈으로 확인할 수 있도록,
시세에 찍힌 거래소 시각(time)을 그대로 함께 담는다.
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json,*/*",
}

SYMBOLS = [("spx", "GSPC"), ("ndx", "NDX")]


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def quote(symbol):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/%5E{symbol}"
           "?range=1d&interval=5m")
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                payload = json.loads(r.read())
            break
        except Exception as e:                        # noqa: BLE001
            last = e
            time.sleep(3)
    else:
        raise last

    m = payload["chart"]["result"][0]["meta"]
    price = m.get("regularMarketPrice")
    if price is None:
        raise RuntimeError("regularMarketPrice 없음")

    stamp = m.get("regularMarketTime")
    period = (m.get("currentTradingPeriod") or {}).get("regular") or {}
    now = int(time.time())
    is_open = bool(period.get("start", 0) <= now <= period.get("end", 0))

    return {
        "price": round(float(price), 2),
        # 거래소가 이 값을 찍은 시각. 여기와 fetched 의 차이가 곧 지연 시간이다.
        "time": iso(stamp) if stamp else None,
        "date": (datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d")
                 if stamp else None),
        "prevClose": (round(float(m["previousClose"]), 2)
                      if m.get("previousClose") is not None else None),
        "open": is_open,
    }


def main():
    out = {
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quotes": {},
    }
    for key, symbol in SYMBOLS:
        try:
            out["quotes"][key] = quote(symbol)
        except Exception as e:                        # noqa: BLE001
            print(f"{key} 실패: {e}", file=sys.stderr)

    if not out["quotes"]:
        raise SystemExit("시세를 하나도 받지 못했습니다.")

    out["open"] = any(q.get("open") for q in out["quotes"].values())
    json.dump(out, sys.stdout, separators=(",", ":"))
    print(f"\n받음: {list(out['quotes'])} / 장 열림: {out['open']}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
