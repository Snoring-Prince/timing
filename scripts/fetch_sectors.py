#!/usr/bin/env python3
"""CUSIP → 업종(SIC). 종목 이름 옆에 적는 섹터를 채웁니다.

어디서 오나
-----------
**SEC 가 회사마다 업종 코드(SIC)를 매겨 둡니다.** 새 출처가 필요 없습니다 —
이 저장소는 이미 `SEC_CONTACT` 를 갖고 있고, `fetch_tickers.py` 가 만든
이름 대조(회사 이름 → CIK)를 그대로 씁니다.

```
공시의 이름  CHEVRON CORP NEW
  → SEC 이름 표에서 CIK 93410
  → data.sec.gov/submissions/CIK0000093410.json  의 앞부분
     "sic":"2911","sicDescription":"Petroleum Refining"
  → 화면에서  석유·정유 / Petroleum Refining
```

**앞부분만 읽습니다.** submissions 파일에는 최근 공시 목록이 통째로 들어 있어
회사에 따라 몇 MB 입니다. `sic` 은 파일 맨 앞에 있으므로 그만큼만 받고 끊습니다
(223개 × 몇 MB 를 매주 받을 수는 없습니다). 못 찾으면 조금 더 읽습니다.

**압축을 요청하지 않습니다.** 앞부분만 읽는 것과 gzip 은 같이 못 갑니다.
그래도 압축해서 보내는 경우를 대비해 매직 바이트를 보고 통째로 다시 받습니다 —
`fetch_tickers.py` 가 SEC 표를 gzip 인 채로 파싱하려다 통째로 실패한 적이
있습니다(로그에 `\\x1f\\x8b` 가 찍혀서 잡았습니다).

한 회사로 좁혀질 때만 받습니다
------------------------------
이름이 여러 회사에 걸리면 버립니다. **틀린 섹터를 적는 것보다 안 적는 것이
낫습니다** — 화면은 섹터가 없으면 그 자리를 비웁니다.

이미 물어본 것은 다시 묻지 않습니다
-----------------------------------
찾은 것은 코드를, 못 찾은 것은 빈 값을 적어 둡니다. 안 적어 두면 매주 다시 묻고
매주 실패합니다(CLAUDE.md 6-2). `RETRY_DAYS` 뒤에 한 번 더 물어봅니다.

**실패로 끝내는 경우는 하나뿐입니다**: 물어볼 것이 있는데 **응답이 하나도 오지
않았을 때**. SEC 가 답하면서 그런 회사를 모른다고 하는 것은 고장이 아닙니다.
"""
import datetime as dt
import gzip, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_tickers import sec_index, sec_lookup, load_json   # 이름 대조를 함께 씁니다

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "data" / "titans" / "berkshire.json"
OUT  = ROOT / "data" / "titans" / "sectors.json"
SUB  = "https://data.sec.gov/submissions/CIK{:010d}.json"
PAUSE = 0.15        # SEC 한도는 초당 10건 — 넉넉히 아래로
HEAD = 16384        # 앞부분만 읽는 크기. sic 은 파일 맨 앞에 있습니다.
MAXREAD = 1 << 19   # 그래도 없으면 여기까지만 더 읽고 포기
RETRY_DAYS = 90
# **이름 대조를 고치면 이 값을 올리세요.** 못 찾은 것은 빈 값으로 굳어 있어서
# 그냥 두면 90일 뒤에나 다시 묻습니다. 첫 실행에서 221개 중 61개가 이름으로
# 안 좁혀졌고(애플·D R 호턴 포함), 열쇠를 층으로 나눠 고친 지금이 그 경우입니다.
SOURCES = "sec-sic2"  # 바뀌면 못 찾은 것을 전부 다시 물어봅니다

SIC = re.compile(r'"sic"\s*:\s*"?(\d{2,4})"?.{0,40}?"sicDescription"\s*:\s*"([^"]*)"', re.S)


def sic_of(cik: str, contact: str):
    """submissions 파일의 앞부분에서 sic 과 설명을 꺼냅니다. (코드, 설명, 원본조각)"""
    url = SUB.format(int(cik))
    req = urllib.request.Request(url, headers={"User-Agent": contact,
                                               "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read(HEAD)
        if raw[:2] == b"\x1f\x8b":          # 안 시켰는데 압축해 보낸 경우
            raw = gzip.decompress(raw + r.read())
        else:
            while len(raw) < MAXREAD and not SIC.search(raw.decode("utf-8", "replace")):
                more = r.read(HEAD)
                if not more:
                    break
                raw += more
    text = raw.decode("utf-8", "replace")
    m = SIC.search(text)
    return (m.group(1), m.group(2).strip()) if m else ("", ""), text[:200]


def main():
    contact = os.environ.get("SEC_CONTACT", "").strip()
    book = load_json(BOOK, None)
    if not book or not book.get("quarters"):
        print("berkshire.json 을 못 읽었습니다 — 섹터는 건너뜁니다.")
        return 0
    if not contact:
        # SEC 는 이름 없는 요청을 거절합니다. 비밀값이 없으면 이 길은 잠깁니다.
        print("SEC_CONTACT 가 없어 섹터를 건너뜁니다.")
        return 0

    # 발행사(CUSIP 앞 여섯 자리)마다 **가장 최근 분기의 이름**을 씁니다.
    # 가장 긴 이름을 고르면 옛 텍스트 공시의 찌꺼기가 이깁니다(CLAUDE.md 9-3).
    name = {}
    for q in book["quarters"]:
        for h in q.get("holdings", []):
            c = str(h.get("cusip", ""))
            if len(c) == 9:
                name[c[:6]] = h.get("name", "")

    have = load_json(OUT, {})
    asked = have.pop("_asked", "")
    src = have.pop("_sources", "")
    today = dt.date.today()
    try:
        old = (today - dt.date.fromisoformat(asked)).days >= RETRY_DAYS
    except Exception:
        old = True

    fresh = sorted(k for k in name if k not in have)
    stale = sorted(k for k in name
                   if k in have and not (have[k] or {}).get("sic")) if (old or src != SOURCES) else []
    todo = fresh + stale
    print(f"발행사 {len(name)}개 · 아는 것 {sum(1 for v in have.values() if (v or {}).get('sic'))}개")
    print(f"물어볼 것 {len(todo)}개 (처음 {len(fresh)} · 다시 {len(stale)})", flush=True)
    if not todo:
        print("새로 물어볼 것이 없습니다.")
        return 0

    try:
        idx = sec_index(contact)
    except Exception as e:
        print(f"SEC 이름 표를 못 받았습니다 — {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    got, answered, shown = {}, False, False
    for k in todo:
        t, title, cik = sec_lookup(idx, name.get(k, ""))
        if not cik:
            print(f"  {k}  {name.get(k,'')[:30]:<30} → 이름으로 못 좁힘")
            continue
        try:
            (code, desc), head = sic_of(cik, contact)
            answered = True
            if not shown:
                # **저쪽이 실제로 보낸 것을 한 번 남깁니다.** 개발 환경에서
                # SEC 가 막혀 있어 응답 모양을 짐작해서 짤 수는 없습니다(9-3).
                print(f"  응답 앞부분: {head}", flush=True)
                shown = True
        except Exception as e:
            print(f"  {k}  {name.get(k,'')[:30]:<30} → 실패 {type(e).__name__}: {e}")
            time.sleep(PAUSE)
            continue
        got[k] = {"sic": code, "desc": desc, "cik": str(int(cik))}
        print(f"  {k}  {name.get(k,'')[:30]:<30} → {code or '없음':<5} {desc}  (SEC: {title})",
              flush=True)
        time.sleep(PAUSE)

    if not answered:
        print("\nSEC 에 닿지 못했습니다 — 응답이 하나도 오지 않았습니다.", file=sys.stderr)
        return 1

    # 못 찾은 것도 적어 둔다. 안 적으면 매주 다시 묻는다.
    for k in todo:
        have[k] = got.get(k, {"sic": "", "desc": "", "cik": ""})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    have["_asked"] = today.isoformat()
    have["_sources"] = SOURCES
    OUT.write_text(json.dumps(have, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    n = sum(1 for k, v in have.items() if k[0] != "_" and (v or {}).get("sic"))
    print(f"\ndata/titans/sectors.json 에 {len(have)-2}개 저장 (업종을 아는 것 {n}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
