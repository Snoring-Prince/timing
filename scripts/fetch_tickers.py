#!/usr/bin/env python3
"""CUSIP → 티커. 로고를 찾는 데 쓰는 마지막 조각입니다.

왜 필요한가
-----------
화면(`titans/index.html`)은 로고를 **ISIN** 으로 찾습니다. 미국 종목의 ISIN 은
"US" + CUSIP 아홉 자리 + 체크숫자라서 공시만 있으면 계산됩니다 — 표가 필요 없습니다.

**그런데 미국 발행사가 아니면 그 계산이 안 됩니다.** CUSIP 첫 글자가 숫자가 아닌
것들(CINS)인데, 버뮤다·케이맨·아일랜드·스위스 법인이 여기 해당합니다.
28년치 223개 묶음 중 13개(5.8%)가 그렇고, 지금 보유 중인 것은 처브 하나입니다.

손으로 적어 넣을 수도 있지만 **매니저를 더 넣으면 계속 늘어납니다.** 사람이
붙어야 하는 표는 결국 낡습니다. 그래서 기계가 채웁니다.

어디서 받나
-----------
**OpenFIGI** (Bloomberg 가 여는 표준). CUSIP 으로 티커를 찾는 용도로 만들어진
곳이고 키 없이 씁니다(키 없을 때 분당 25요청 · 요청당 10건).
**여기서 받아 저장소에 두고, 방문자 브라우저는 이 파일만 읽습니다** — 방문자가
OpenFIGI 로 직접 나가지 않으므로 IP 도 안 새고 화면이 그쪽에 묶이지도 않습니다.

**개발 환경에서는 막혀 있습니다**(`000`). 러너에서 돌려야 합니다 — SEC·야후와 같습니다.

이미 물어본 것은 다시 묻지 않습니다
-----------------------------------
찾은 것은 티커를, **못 찾은 것은 빈 문자열을** 적어 둡니다. 옛 종목의 사라진
주식 종류(리버티글로벌 4종 같은 것)는 OpenFIGI 에도 없어서 영영 못 찾는데,
그걸 기록하지 않으면 **매주 다시 묻고 매주 실패합니다.** 이 프로젝트가 이미
적어 둔 함정입니다 — "매주 실패하면 아무도 안 봅니다"(CLAUDE.md 6-2).

못 찾은 것도 `RETRY_DAYS` 뒤에는 한 번 더 물어봅니다. 나중에 등록될 수 있으니까요.

**실패로 끝내는 경우는 하나뿐입니다**: 한 번도 안 물어본 종목이 있는데 그중
하나도 못 받았을 때. 그때는 OpenFIGI 가 막혔다는 뜻이라 빨간 X 로 보여야 합니다.
옛 종목이 계속 안 잡히는 것은 실패가 아닙니다.

**`_` 로 시작하는 키는 화면이 무시합니다.** 파일에 언제 물어봤는지를 같이 둡니다.
"""
import datetime as dt
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "data" / "titans" / "berkshire.json"
OUT  = ROOT / "data" / "titans" / "tickers.json"
API  = "https://api.openfigi.com/v3/mapping"
BATCH = 10          # 키 없을 때 요청당 최대 10건
PAUSE = 3.0         # 분당 25요청 한도 — 넉넉히 띄운다
RETRY_DAYS = 90     # 못 찾은 것을 다시 물어보기까지


def needs_ticker(cusip: str) -> bool:
    """ISIN 을 만들 수 없는 것만 고른다.

    첫 글자가 숫자면 미국 발행사이고 화면이 ISIN 을 직접 계산한다.
    여기서 물을 이유가 없다 — 요청을 아끼는 것이 아니라, 물어볼 필요가 없다.
    """
    return len(cusip) == 9 and not cusip[0].isdigit()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def ask(cusips):
    """OpenFIGI 에 한 묶음을 묻는다. 돌려주는 것은 {cusip: ticker}."""
    body = json.dumps([{"idType": "ID_CUSIP", "idValue": c} for c in cusips]).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "itpaidoff.com titans (github.com/Snoring-Prince/timing)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.loads(r.read().decode())

    out = {}
    # 응답은 보낸 순서대로 온다. 항목마다 data(성공) 또는 warning(못 찾음).
    for cusip, row in zip(cusips, rows):
        hits = (row or {}).get("data") or []
        if not hits:
            continue
        # 한 CUSIP 에 거래소별로 여러 줄이 온다. 미국 상장분을 먼저 고른다 —
        # 13F 는 미국 상장 종목만 담으므로 그쪽이 화면에 찍히는 것과 맞는다.
        pick = next((h for h in hits if h.get("exchCode") == "US"), hits[0])
        t = (pick.get("ticker") or "").strip().upper()
        if t:
            out[cusip] = t
    return out


def main():
    book = load_json(BOOK, None)
    if not book or not book.get("quarters"):
        print("berkshire.json 을 못 읽었습니다 — 티커는 건너뜁니다.")
        return 0

    # 28년치 전부에서 모은다. 옛 종목도 나중에 '일생' 화면에서 쓴다.
    wanted, name = set(), {}
    for q in book["quarters"]:
        for h in q.get("holdings", []):
            c = h.get("cusip", "")
            if needs_ticker(c):
                wanted.add(c)
                name[c] = h.get("name", "")

    have = load_json(OUT, {})
    asked = have.pop("_asked", "")          # 화면이 무시하는 키. 쓸 때 다시 넣는다.
    today = dt.date.today()

    fresh = sorted(wanted - set(have))      # 한 번도 안 물어본 것
    stale = []                              # 못 찾았던 것 — 오래됐으면 한 번 더
    try:
        old = (today - dt.date.fromisoformat(asked)).days >= RETRY_DAYS
    except Exception:
        old = True
    if old:
        stale = sorted(c for c in wanted if c in have and not have[c])

    todo = fresh + stale
    print(f"ISIN 을 못 만드는 종목 {len(wanted)}개 · 아는 것 "
          f"{sum(1 for c in have.values() if c)}개 · 못 찾은 것 "
          f"{sum(1 for c in have.values() if not c)}개")
    print(f"물어볼 것 {len(todo)}개 (처음 {len(fresh)} · 다시 {len(stale)})")
    if not todo:
        print("새로 물어볼 것이 없습니다.")
        return 0

    got, failed = {}, []
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        try:
            got.update(ask(chunk))
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} — {chunk[0]} 외 {len(chunk)-1}건")
            failed += chunk
        except Exception as e:
            print(f"  실패 {type(e).__name__}: {e}")
            failed += chunk
        if i + BATCH < len(todo):
            time.sleep(PAUSE)

    for c in todo:
        print(f"  {c}  {name.get(c,'')[:30]:<30} → {got.get(c) or '못 찾음'}")

    # **처음 물어본 것이 있는데 그중 하나도 못 받았으면** OpenFIGI 가 막힌 것이다.
    # 옛 종목이 계속 안 잡히는 것은 실패가 아니다 — 그건 원래 없는 것이다.
    if fresh and not any(c in got for c in fresh):
        print("\n처음 물어본 종목을 하나도 받지 못했습니다 — OpenFIGI 가 막혔을 수 있습니다.",
              file=sys.stderr)
        return 1

    # 못 찾은 것도 빈 값으로 적어 둔다. 안 적으면 매주 다시 묻고 매주 실패한다.
    for c in todo:
        have[c] = got.get(c, "")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    have["_asked"] = today.isoformat()
    OUT.write_text(json.dumps(have, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    have.pop("_asked")
    try:
        where = OUT.relative_to(ROOT)
    except ValueError:          # 시험할 때 다른 자리에 쓰는 경우
        where = OUT
    print(f"\n{where} 에 {len(have)}개 저장 (이번에 새로 찾은 것 {len(got)}개)")
    if failed:
        print(f"못 받은 것 {len(failed)}개 — 다음 주에 다시 묻습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
