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
import sys
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_tickers import norm  # noqa: E402
from titans import registry  # noqa: E402
from titans.registry import books, is_share  # noqa: E402

OUT = ROOT / "data/titans/prices.json"
# 방문자는 공유 창고(OUT)가 아니라 **자기 투자자의 몫**만 받는다.
# 창고는 봇이 쓰는 것이다 — 같은 종목을 여러 투자자가 들고 있어도 한 번만
# 받고, 분할을 한 번만 훑는다. 투자자 몫은 그 창고에서 잘라 낸 것이라 손으로
# 고치지 않는다(대시보드의 `data/dashboard/` 와 같은 요령).
PER = ROOT / "data/titans/prices"
UTC = dt.timezone.utc
NY = ZoneInfo("America/New_York")
# 가격은 15년치만 저장하지만 **분할은 그 종목이 공시에 처음 나온 분기까지**
# 훑는다. 화면은 붙어 있는 두 공시 사이만 묻고(`realSplit(key, QS[i-1], QS[i])`),
# 그 종목을 들고 있기 시작한 분기보다 옛 분할은 물어볼 일이 아예 없다.
# 월봉으로 싸게 받을 수는 없다 — 정찰(2026-09-23)에서 AXP 1983-02-11 4:3 이
# 월봉 응답에만 빠져 있었다. 그래서 일봉으로 받고 창 밖의 옛 바는 버린다.


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
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 2 or getattr(exc, "code", None) == 404:
                raise
            time.sleep(5*(attempt+1))


def first_seen(books):
    """종목마다 **처음 공시에 나온 분기** — 분할을 얼마나 깊이 훑을지 정한다."""
    seen = {}
    for book in books:
        for quarter in book.get("quarters", []):
            for h in quarter["holdings"]:
                if is_share(h) and seen.get(h["cusip"], "9999") > quarter["period"]:
                    seen[h["cusip"]] = quarter["period"]
    return seen


def required_cusips(books):
    """Cache every current share class; a new investor reuses the same CUSIP."""
    required = {}
    for book in books:
        quarters = book.get("quarters", [])
        if not quarters:
            continue
        latest = max(quarters, key=lambda q: q["period"])
        for h in latest["holdings"]:
            if is_share(h) and h.get("shares", 0) > 0 and h.get("value", 0) > 0:
                required[h["cusip"]] = {"name": h["name"], "class": h.get("class", "")}
    return required


def marks(books):
    """종목마다 **가장 최근 공시의 분기말 가격**(금액 ÷ 주식수)과 그 날짜.

    번호로 짝을 못 찾아 이름으로 붙인 티커를 확인하는 자다. 이미 붙어 있는
    102종목을 재 보니 99개는 공시 금액 ÷ 주식수와 그날 종가가 소수 여섯째
    자리까지 같았고, 가장 먼 것도 0.73% 였다(2026-09-28).

    그래서 문턱은 2% 다. 처음엔 0.5% 였는데 토름(TRMD)이 +1.06% 로 떨어졌다 —
    코펜하겐에도 상장된 회사라 공시가 그쪽 종가를 달러로 바꿔 적은 것으로
    보인다. 엉뚱한 종목이면 보통 이보다 훨씬 벌어지고, 같은 회사의 다른 보통주
    (A·C)는 이 자가 아니라 '보통주가 둘이면 안 붙인다' 규칙이 막는다."""
    got = {}
    for book in books:
        quarters = book.get("quarters", [])
        if not quarters:
            continue
        latest = max(quarters, key=lambda q: q["period"])
        for h in latest["holdings"]:
            if is_share(h) and h.get("shares", 0) > 0 and h.get("value", 0) > 0:
                if got.get(h["cusip"], ("",))[0] < latest["period"]:
                    got[h["cusip"]] = (latest["period"], h["value"]/h["shares"])
    return got


def mark_close(values, splits, mark):
    """공시 분기말에 가장 가까운 종가(그 뒤 분할만큼 되돌림)와 그 날짜. 없으면 None."""
    day, _ = mark
    near = [(d, v) for d, v in values if d <= day]
    if not near or (dt.date.fromisoformat(day)-dt.date.fromisoformat(near[-1][0])).days > 5:
        return None
    close = near[-1][1]
    for when, ratio in splits.items():
        if near[-1][0] < when:
            num, den = (float(x) for x in ratio.split(":"))
            close *= num/den
    return near[-1][0], close


def mark_matches(values, splits, mark, tolerance=.02):
    """분기말 종가(그 뒤 분할만큼 되돌림)가 공시의 금액 ÷ 주식수와 맞는가."""
    got = mark_close(values, splits, mark)
    return bool(got) and abs(got[1]/mark[1]-1) <= tolerance


class Unpriced(ValueError):
    """고장이 아니라 **답이 '없다'로 온 것** — 번호로도 이름으로도 짝이 없거나,
    시세 쪽이 그 티커를 모른다. 매일 빨간불로 울리면 진짜 고장이 묻히므로
    처음 볼 때 한 번만 울리고 목록(`unpriced`)에 적는다. 그 줄은 화면에서
    분기말 가격으로만 그린다."""


def resolve(cusips, required, known, unverified=None):
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
    # usable only for the sole plain ordinary class and a verified US share
    # issuer match. Never apply this fallback to A/B/C, preferred or ADR classes.
    # 같은 회사의 워런트(`WARRANT`)는 주식 종류가 아니다. 주식과 워런트를 같이
    # 들고 있어도 보통주가 하나뿐이면 가릴 것이 없다(오크트리 Rice·Alvotech).
    for cusip in cusips:
        identity = required[cusip]
        issuer_classes = [c for c in required if c[:6] == cusip[:6]
                          and PLAIN.fullmatch(required[c]["class"].upper().strip())]
        if cusip in result or cusip[0].isdigit() or len(issuer_classes) != 1 or not PLAIN.fullmatch(identity["class"].upper().strip()):
            continue
        ticker = known.get(cusip)
        if not ticker:
            continue
        rows = request("https://api.openfigi.com/v3/mapping", [
            {"idType": "TICKER", "idValue": ticker, "exchCode": "US"}])
        data = rows[0].get("data", []) if isinstance(rows, list) and rows else []
        candidates = [r for r in data if r.get("ticker") == ticker
                      and r.get("securityType") in SHARE_TYPES
                      and same_issuer(r.get("name", ""), identity["name"])]
        if candidates and len({r.get("shareClassFIGI") for r in candidates}) == 1:
            result[cusip] = ticker
            # 이름으로 붙인 것은 종가를 받은 뒤 분기말 가격으로 한 번 더 잰다.
            if unverified is not None:
                unverified.add(cusip)
        else:
            # 왜 못 붙였는지 **원본을 찍는다.** 개발 환경에서 OpenFIGI 가 막혀 있어
            # 응답 모양을 짐작으로 맞춘 자리다(9-3 — gzip·OpenFIGI 때 두 번 틀림).
            print(f"{cusip} {ticker}: fallback rejected · raw {json.dumps(rows, ensure_ascii=False)[:600]}", flush=True)
    return result


# 해외 법인이 미국에 낸 **한 종류뿐인 보통주**의 공시 표기. 네덜란드 법인의
# 뉴욕 등록주(ASML `N Y REGISTRY SHS`)도 여기 든다 — ADR 이 아니라 본주 그대로다.
# 종류 글자(CL A·SHS CL C)·우선주·단위(UNIT)는 넣지 않는다. 허벌라이프는
# `COM SHS` 로 적는다(바우포스트 2026-06-30).
PLAIN = re.compile(r"COM(?:MON)?(?: STOCK| SHS)?|SHS|ORD(?: SHS)?|ORDINARY SHARES|"
                   r"N ?Y REGISTRY SHS|NY REG(?:ISTRY)? SHS|REG SHS|NAMEN AKT")
# OpenFIGI 의 securityType. 뉴욕 등록주는 'NY Reg Shrs' 로 온다(2026-09-28 러너 실측 —
# 넓은 칸 securityType2 는 'Depositary Receipt' 라 그쪽으로는 가릴 수 없다). ADR 은 'ADR'.
SHARE_TYPES = {"Common Stock", "NY Reg Shrs"}
# 회사 이름이 아니라 **주식 종류**를 적은 낱말. OpenFIGI 는 뉴욕 등록주 이름 끝에
# 종류를 붙인다: 'ASML HOLDING NV-NY REG SHS'(실측). 공시는 'ASML HLDG NV'.
NOT_NAME = {"HLDG", "NY", "N", "Y", "REG", "REGISTRY", "SHS"}


def same_issuer(figi, filed):
    """공시는 `ASML HLDG NV`, OpenFIGI 는 `ASML HOLDING NV-NY REG SHS` 로 적는다.

    OpenFIGI 는 A주에 꼬리를 단다: `TORM PLC-A`, `XP INC - CLASS A`,
    `LIBERTY GLOBAL LTD-A`(2026-09-28 러너 실측). 공시는 `TORM PLC` 뿐이다.
    **A 만** 떼고 B·C 는 남긴다 — B·C 꼬리면 공시와 다른 종류일 수 있다.
    A 를 떼어 붙인 것도 종가를 받은 뒤 분기말 가격으로 다시 잰다(`mark_matches`).

    바우포스트에서 두 가지가 더 나왔다(2026-09-28 러너 실측).
    - 줄임말: 공시 `AXALTA COATING SYS LTD` · OpenFIGI `AXALTA COATING SYSTEMS LTD`.
      그래서 낱말끼리 한쪽이 다른 쪽의 앞부분(3글자 이상)이어도 같다고 본다.
    - 잘린 이름: OpenFIGI `NORWEGIAN CRUISE LINE HOLDIN` — 28글자에서 끊겼다.
      28글자 이상이면 끝 낱말은 잘렸을 수 있어 빼고, 남은 낱말이 공시 이름의
      앞부분과 맞는지 본다. 이렇게 붙인 것도 전부 종가 대조를 한 번 더 거친다."""
    words = lambda n: [w for w in norm(n) if w not in NOT_NAME]
    a, b = words(figi), words(filed)
    if a[-1:] == ["A"] and b[-1:] != ["A"]:
        a = a[:-1]
    if sorted(a) == sorted(b):
        return True
    if len(str(figi).strip()) >= 28 and len(a) >= 3:
        a = a[:-1]
        b = b[:len(a)]
    same = lambda x, y: x == y or (min(len(x), len(y)) >= 3 and (x.startswith(y) or y.startswith(x)))
    return len(a) == len(b) >= 1 and all(same(x, y) for x, y in zip(a, b))


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
        if len([day for day in incoming if day >= start]) < len(expected)*.98:
            raise ValueError("full refresh is unexpectedly shorter than saved history")
    merged = incoming if full else previous | incoming
    return {"values": [[day, merged[day]] for day in sorted(merged) if day >= start], "splits": splits}


def collect(required, previous, now, full=False, known=None, since=None, quarter_marks=None):
    saved = previous.get("series", {})
    # Weekly/full verification also catches ticker changes of the same security.
    missing = [c for c in required if full or now.weekday() == 5 or not saved.get(c, {}).get("ticker")]
    # **팔린 종목은 방문자 파일에 안 쌓는다.** 이 파일은 방문자가 통째로 받는
    # 것인데 화면이 읽는 것은 지금 보유 종목뿐이다. 그대로 두면 버크셔 한
    # 명만으로 242종목 18MB, 여덟 명이면 73MB 가 된다(2026-09-23 실측).
    # 버리는 값은 재진입 때 한 번 다시 받는 것뿐이고(28년에 37번 · 요청 1번 ·
    # 74KB), 그 길은 새 종목이 처음 들어올 때와 같은 길이라 이미 돈다 —
    # 파일에 없으면 **그 종목이 공시에 처음 나온 분기까지** 다시 훑으므로
    # 안 들고 있던 사이의 분할·분사도 그 한 번에 같이 들어온다.
    # 받기에 실패한 종목은 보유 목록에 그대로 있으므로 옛 값이 남는다.
    series = {c: saved[c] for c in required if c in saved}
    errors = []
    unpriced = {}
    unverified = set()
    try:
        mapped = resolve(missing, required, known or {}, unverified) if missing else {}
        answered = True
    except Exception as exc:
        mapped = {}
        errors.append(f"ticker mapping unavailable: {exc}")
        # OpenFIGI 가 **답을 못 한** 날의 '짝 없음'은 알려진 상태가 아니라 고장이다.
        answered = False
    start = years_before(now.astimezone(NY).date())-dt.timedelta(days=7)
    for cusip, identity in sorted(required.items()):
        old = saved.get(cusip, {})
        ticker = mapped.get(cusip) or old.get("ticker")
        try:
            if not ticker:
                raise (Unpriced if answered else ValueError)("exact CUSIP mapping unavailable")
            refresh = full or not old.get("values") or now.weekday() == 5
            # 상장 때부터는 **종목마다 한 번만** 훑는다. 1983년 분할은 앞으로도
            # 1983년 분할이라, 매주 40년치 바를 다시 받아 같은 답을 얻는 것은
            # 낭비다(주 1회 10.8MB → 33MB). 이미 훑어 둔 종목은 예전처럼 15년
            # 창만 받고, 창 밖 분할은 저장된 책에서 가져온다.
            # 15년 창보다 늦게 들어온 종목이라도 가격은 창을 채워야 한다.
            need = min((since or {}).get(cusip, start.isoformat()), start.isoformat())
            scanned = old.get("splitsFrom") if old.get("ticker") == ticker else None
            deep = not scanned or scanned > need
            first = ((dt.date.fromisoformat(need) if deep else start) if refresh
                     else dt.date.fromisoformat(old["values"][-1][0])-dt.timedelta(days=10))
            def download(day, verify=False):
                p1 = int(dt.datetime.combine(day, dt.time(), NY).timestamp())
                url = ("https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(ticker, safe="")+
                       f"?period1={p1}&period2={int(now.timestamp())}&interval=1d&events=splits")
                try:
                    payload = request(url)
                except urllib.error.HTTPError as exc:
                    # 한 번도 받은 적 없는 티커를 시세 쪽이 모른다(상장 폐지 등).
                    # 받아 둔 종가가 있던 티커가 사라진 것은 고장으로 남긴다.
                    if exc.code == 404 and not old.get("values"):
                        raise Unpriced(f"price source does not know {ticker}") from exc
                    raise
                parsed = parse_chart(payload, ticker, now)
                first_trade = payload["chart"]["result"][0]["meta"].get("firstTradeDate")
                if verify and first_trade:
                    expected = max(day, from_epoch(first_trade).astimezone(NY).date())
                    if dt.date.fromisoformat(parsed[0][0][0]) > expected+dt.timedelta(days=14):
                        raise ValueError("response starts too late for a full history")
                    elapsed = (dt.date.fromisoformat(parsed[0][-1][0])-expected).days
                    if len(parsed[0]) < elapsed/365.25*252*.75:
                        raise ValueError("full history has unexpectedly few daily prices")
                return parsed
            values, splits = download(first, refresh)
            # Incremental responses only contain recent split events. Compare those;
            # a newly reported or changed event forces an entire history download.
            if not refresh:
                if any(old.get("splits", {}).get(day) != ratio for day, ratio in splits.items()):
                    refresh = True
                    values, splits = download(dt.date.fromisoformat(need) if deep else start, True)
                else:
                    splits = old.get("splits", {}) | splits
            if refresh and not deep:
                # 이 응답에는 창 밖 분할이 없다. 지우지 말고 책에서 되살린다.
                splits = {d: v for d, v in old.get("splits", {}).items()
                          if d < start.isoformat()} | splits
            if (now.astimezone(NY).date()-dt.date.fromisoformat(values[-1][0])).days > 7:
                raise ValueError("last closing price is more than seven days old")
            mark = (quarter_marks or {}).get(cusip, ("", 0))
            if cusip in unverified and not mark_matches(values, splits, mark):
                # 이름으로 붙인 티커가 다른 종류(A↔C)거나 다른 회사면 여기서 걸린다.
                # **얼마나 어긋났는지 숫자를 남긴다** — 오크트리의 토름(1위)이 여기
                # 걸렸는데 숫자가 없어 티커가 틀린 것인지 공시 기준가가 다른 것인지
                # (예: 코펜하겐 종가) 가릴 수 없었다(2026-09-28).
                got = mark_close(values, splits, mark)
                seen = (f"close {got[1]:.4f} on {got[0]} vs filing {mark[1]:.4f} for {mark[0]} "
                        f"({got[1]/mark[1]-1:+.2%})" if got else f"no close near {mark[0] or 'the filing date'}")
                raise Unpriced(f"{ticker} failed the quarter-end price check: {seen}")
            if refresh and deep:
                scanned = need
            series[cusip] = {**identity, "ticker": ticker, "currency": "USD",
                            **merge_series(old, values, splits, start.isoformat(), refresh),
                            **({"splitsFrom": scanned} if scanned else {})}
            print(f"{cusip} {ticker}: {len(series[cusip]['values'])} days, last {series[cusip]['values'][-1][0]}", flush=True)
        except Unpriced as exc:
            unpriced[cusip] = {"ticker": ticker or "", "reason": str(exc)}
        except Exception as exc:
            errors.append(f"{cusip} {ticker or '?'}: {exc}")
        time.sleep(.3)
    result = {"method": "split-adjusted-close", "series": series}
    if unpriced:
        result["unpriced"] = unpriced
    return result, errors


def write_if_changed(path, data):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))+"\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return True


def publish(cache, pairs, folder=None):
    """투자자마다 **그 사람의 최신 보유 종목만** 담은 파일을 쓴다.

    여덟 명이 한 파일을 같이 쓰면 버크셔 화면을 여는 사람도 여덟 명분을
    받는다. 창고에 아직 없는 종목(오늘 처음 들어온 것)은 빠지고, 화면은 그
    줄만 분기말 가격으로 그린다 — 지금과 같다."""
    folder = folder or PER
    series = cache.get("series", {})
    written = []
    for slug, book in pairs:
        own = {c: series[c] for c in sorted(required_cusips([book])) if c in series}
        if write_if_changed(folder / f"{slug}.json",
                            {"method": cache.get("method", "split-adjusted-close"), "series": own}):
            written.append(slug)
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--publish", action="store_true",
                        help="받지 않고 창고에서 투자자별 파일만 다시 만든다")
    args = parser.parse_args()
    investors = registry.load()
    # 방금 등록해 공시를 한 번도 안 받은 투자자는 건너뜁니다. 책도 투자자 파일도
    # 없으면 지킬 가격이 아직 없습니다. 둘 중 하나라도 있으면 strict 가 멈춥니다 —
    # 책만 사라진 것을 전량 매도로 읽어 가격을 지우면 안 되기 때문입니다.
    fresh = [i for i in investors
             if not i.output.exists() and not (PER / f"{i.slug}.json").exists()]
    for investor in fresh:
        print(f"{investor.slug}: 공시도 주가 파일도 아직 없습니다 — 이번에는 건너뛰고 창고에서 아무것도 안 지웁니다")
    investors = [i for i in investors if i not in fresh]
    catalog = books(investors, strict=True)
    required = required_cusips(catalog)
    # 모든 활성 투자자의 책이 있어야 매도 여부를 알 수 있습니다(strict=True).
    # 전체 보유 목록이 비어도 기존 가격 캐시를 보존합니다.
    if not required:
        raise SystemExit("no investor book holds anything: refusing to rewrite the price cache")
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    # strict=True 라 책은 투자자 순서대로 빠짐없이 온다.
    pairs = list(zip([i.slug for i in investors], catalog))
    if args.publish:
        print("다시 쓴 투자자 파일:", publish(previous, pairs) or "없음")
        return
    known = json.loads((ROOT / "data/titans/tickers.json").read_text(encoding="utf-8"))
    result, errors = collect(required, previous, dt.datetime.now(UTC), args.full, known,
                             first_seen(catalog), marks(catalog))
    if fresh:
        # 건너뛴 투자자가 있으면 창고에서 아무것도 지우지 않습니다. 정말 새 투자자면
        # 지울 것이 없고, 혹시 책과 투자자 파일을 둘 다 잃은 것이라면 그 가격을
        # 매도로 읽어 지우면 안 됩니다.
        kept = previous.get("series", {})
        result["series"] = {**{c: kept[c] for c in kept if c not in result["series"]},
                            **result["series"]}
    if (result["series"] != previous.get("series", {})
            or result.get("unpriced", {}) != previous.get("unpriced", {})):
        write_if_changed(OUT, result)
    # 받기에 실패한 종목이 있어도 받은 것은 투자자 파일까지 내보낸다.
    publish(result, pairs)
    # 짝이 없는 종목은 **처음 볼 때만** 빨간불로 알린다. 오크트리처럼 워런트·
    # 해외 두 종류 주식을 든 투자자는 이런 줄이 늘 몇 개 있어서, 매일 울리면
    # 진짜 고장(통신·형식)이 묻힌다(6-2). 고장은 지금처럼 매번 빨간불이다.
    seen = previous.get("unpriced", {})
    unpriced = result.get("unpriced", {})
    for cusip, why in sorted(unpriced.items()):
        if cusip in seen:
            print(f"{cusip} {why['ticker'] or '?'}: 알려진 상태 — 분기말 가격으로만 그립니다 ({why['reason']})")
    news = [f"{c} {w['ticker'] or '?'}: {w['reason']} — 처음 봄, 이 줄은 분기말 가격으로만 그립니다"
            for c, w in sorted(unpriced.items()) if c not in seen]
    if errors or news:
        raise SystemExit("\n".join(errors + news))


if __name__ == "__main__":
    main()
