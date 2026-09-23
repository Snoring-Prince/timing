"""
대가들의 선택 — 액면분할 이력 정찰(probe)

**이 스크립트는 파서가 아닙니다.** 받아서 재고 원본을 그대로 저장할 뿐입니다.
`probe_sec.py`·`probe_amendments.py` 와 같은 요령이고, 같은 이유로 따로 있습니다.

무엇을 알아내려는 것인가
------------------------

13F 에는 "액면분할을 했다"는 말이 없습니다. 주식수와 금액뿐입니다. 그래서
화면은 **주식수가 뛰면서 가격이 그만큼 내려간 분기**를 분할로 **추측**해
왔는데, 추측으로는 못 푸는 자리가 있습니다.

    5:4 (1.25배) · 4:3 (1.33배)   '조금 더 산 분기' 와 구별이 안 됩니다
    역분할 (1:10)                  후보에 없어 아예 못 잡습니다

그런데 **`data/titans/prices.json` 에 이미 진짜 분할 기록이 들어 있습니다** —
`fetch_prices.py` 가 종가를 받을 때 `events=splits` 로 같이 받아 둡니다.
화면이 그것을 읽도록 고쳤습니다(2026-09-23). **남은 구멍은 기간 하나뿐입니다.**

    주가 파일이 덮는 구간   2011-09 ~ 지금  (15년)
    공시가 있는 구간        1998-12 ~ 지금  (28년)
                            ↑ 이 사이가 아직 추측입니다
                              (아메리칸익스프레스 3:1 2000년 · 무디스 2:1 2005년)

이 정찰이 답할 질문은 **딱 하나**입니다.

    period1 을 아주 옛날로 주면 야후가 그 시절 분할까지 돌려주는가?
    돌려준다면 어떤 모양으로 오는가?

받은 답 (2026-09-23 · 실행 35827799749 · 다섯 종목 전부 HTTP 200)
--------------------------------------------------------------

    예, 상장 때까지 돌려줍니다.   AXP 1972-06-01 상장 · 분할 6건 (1983년치까지)
                                 KO  1962-01-02 상장 · 분할 6건 (1977년치까지)
    찾던 둘이 그 안에 있습니다.   AXP 2000-05-11 3:1 · MCO 2005-05-19 2:1

    **월봉으로 싸게 받을 수는 없습니다.** AXP 1983-02-11 4:3 이 월봉 응답에만
    통째로 빠져 있었습니다(일봉 6건 · 월봉 5건). 그래서 일봉으로 받고 창 밖의
    옛 바는 버립니다 — `fetch_prices.py` 의 `DEEP` 이 그것입니다.

    그리고 **여기서도 스핀오프가 섞여 옵니다.** AXP 1994-05-31 `10000:8825`
    (리먼)와 2005-10-03 `10000:8753`(아메리프라이즈)은 분할이 아닙니다.
    뒤엣것은 우리 공시 구간 안이라, 분할로 받았으면 숫자가 틀어졌을 자리입니다.
    화면의 `splitRatio()`(기약분수 ≤20)가 둘 다 버립니다.

**짐작해서 수집기를 고치지 않습니다.** 이 저장소는 그 자리에서 이미 두 번
틀렸습니다(gzip 미해제, OpenFIGI 응답 짐작 — `CLAUDE.md` 9-3).

왜 러너에서만 도는가
--------------------

개발 환경에서 `query1.finance.yahoo.com` 은 프록시가 끊습니다
(`CLAUDE.md` 3번 — 2026-09-07 실측). 러너에서는 됩니다.

해석하지 않습니다
-----------------

받은 것을 그대로 저장하고, 상태 코드·크기·분할 항목 수만 셉니다.
**어느 것이 진짜 분할이고 어느 것이 스핀오프인지도 여기서 정하지 않습니다** —
야후의 `splits` 는 분할 목록이 아니라 '주가를 보정해야 하는 사건' 목록이라
스핀오프가 섞여 있습니다(제퍼리스 2023-01-17 `1046:1000` 은 주식수가 안 바뀝니다).
그 판정은 화면 코드(`splitRatio`)가 이미 하고 있고, 여기서는 **원문에 무엇이
들어 있는지만** 봅니다.
"""
import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

OUT = "split-probe"
# 기본 종목은 **지금 화면이 못 덮는 자리**를 고른 것입니다 — 아메리칸익스프레스와
# 무디스는 2011년 이전에 분할했고 지금도 보유 중입니다.
DEFAULT = "AXP,MCO,KO,AAPL,JEF"


def day_of(stamp) -> str:
    """유닉스 초 → 날짜. **음수(1960년대 상장)도 읽혀야 합니다** —
    윈도에서 `fromtimestamp` 가 거기서 터집니다(`fetch_prices.py` 와 같은 이유)."""
    return (dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
            + dt.timedelta(seconds=int(stamp))).date().isoformat()


def fetch(ticker: str, since: str, interval: str):
    """한 종목의 원문을 그대로 받아 옵니다. 해석하지 않습니다."""
    p1 = int(dt.datetime.fromisoformat(since + "T00:00:00+00:00").timestamp())
    p2 = int(dt.datetime.now(dt.timezone.utc).timestamp())
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(ticker, safe="")
           + f"?period1={p1}&period2={p2}&interval={interval}&events=splits")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, res.read(), url
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), url


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=DEFAULT)
    ap.add_argument("--since", default="1970-01-01",
                    help="period1 (이 날부터). 기본은 최대한 옛날")
    ap.add_argument("--intervals", default="1d,1mo",
                    help="일봉과 월봉 둘 다 받아 **분할 목록이 같은지** 봅니다")
    args = ap.parse_args(argv)

    os.makedirs(OUT, exist_ok=True)
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    intervals = [i.strip() for i in args.intervals.split(",") if i.strip()]
    print(f"period1 = {args.since} · 종목 {len(tickers)}개 · 간격 {intervals}\n")

    bad = 0
    for ticker in tickers:
        seen = {}
        for interval in intervals:
            try:
                status, raw, url = fetch(ticker, args.since, interval)
            except Exception as exc:  # noqa: BLE001
                print(f"{ticker:<6} {interval:<4} 받기 실패 — {exc}")
                bad += 1
                continue
            name = f"{OUT}/{ticker}-{interval}.json"
            with open(name, "wb") as f:
                f.write(raw)
            note, splits, rows = "", {}, 0
            try:
                row = json.loads(raw)["chart"]["result"][0]
                splits = row.get("events", {}).get("splits", {}) or {}
                rows = len(row.get("timestamp") or [])
                first = row["meta"].get("firstTradeDate")
                if first:
                    note = "  상장 " + day_of(first)
            except Exception as exc:  # noqa: BLE001
                note = f"  ※ 읽지 못함: {exc}"
                bad += 1
            days = sorted(day_of(v["date"]) + " " + str(
                v.get("splitRatio") or f"{v.get('numerator')}:{v.get('denominator')}")
                for v in splits.values())
            seen[interval] = days
            print(f"{ticker:<6} {interval:<4} HTTP {status} · {len(raw):>9,} bytes · "
                  f"바 {rows:>6,}개 · 분할 {len(days)}건{note}")
            for d in days:
                print(f"         {d}")
        # **간격을 바꿔도 분할 목록이 같은가** — 이 정찰을 만든 질문입니다.
        # 답은 "아니오"로 이미 나왔으므로(위 주석) 다름 자체는 실패가 아닙니다.
        # 실패로 두면 옛 분할이 있는 종목마다 빨간불이 떠서, 진짜 고장이
        # 묻힙니다 — CLAUDE.md 6-2 의 "매주 실패하면 아무도 안 봅니다".
        if len(seen) > 1:
            same = len({json.dumps(v) for v in seen.values()}) == 1
            print(f"       → 간격이 달라도 분할 목록이 {'같습니다' if same else '★ 다릅니다 (알려진 것 — 일봉을 쓰세요)'}")
        print()

    print(f"원본을 {OUT}/ 에 저장했습니다. 해석은 하지 않았습니다.")
    # 손으로 돌린 것은 "되는지 확인해 달라"는 뜻이라, 조용히 넘어가면
    # 초록불인데 빈손이 됩니다(`notify.py --test` 와 같은 이유 — CLAUDE.md 6-2).
    # 빨간불은 **받아오지 못했을 때만**입니다.
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
