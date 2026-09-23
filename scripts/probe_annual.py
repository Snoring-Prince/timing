"""
대가들의 선택 — 버크셔 연차보고서(10-K) 취득원가 정찰(probe)

**이 스크립트는 파서가 아닙니다.** 받아서 재고 원본을 그대로 저장할 뿐입니다.
대조를 어떻게 짤지는 여기서 정하지 않습니다 — 이것을 읽은 뒤에 사람이 정합니다.
`probe_sec.py` · `probe_amendments.py` 와 같은 요령이고, 같은 이유로 따로 있습니다.

무엇을 알아내려는 것인가
------------------------

화면의 수익률은 **추정 매수 평균가**에서 나옵니다. 13F 에는 체결가가 없으므로,
분기마다 늘어난 주식수를 *직전 분기말과 이번 분기말 가격의 중간값*으로 샀다고
보고 이동평균으로 잇습니다. **가운데가 가정입니다.**

그 가정이 맞는지 한 번도 바깥 자료와 맞춰 본 적이 없습니다. stockcircle 과
애플 평균가가 0.1% 차이로 맞았지만 **저쪽도 같은 방법**이라, 산수가 맞다는
뜻이지 답이 맞다는 뜻이 아닙니다(`CLAUDE.md` 9-3).

버크셔를 첫 투자자로 고른 이유가 바로 이것입니다 — **연차보고서가 실제
취득원가를 적는 거의 유일한 곳**입니다. 그 자 하나로 여덟 명 전부에 쓰는
계산 방법을 검증할 수 있습니다.

답할 질문 넷
------------

    A  연차보고서가 **종목별 취득원가**를 적는가? 적는다면 어느 파일 어디에?
    B  그것이 XBRL 로 태그돼 있는가?  ← 자동 대조가 튼튼할지 무를지가 갈립니다
    C  분기보고서(10-Q)에도 있는가?   ← 얼마나 자주 잴 수 있는지가 정해집니다
    D  실리는 종목이 우리 보유와 겹치는가? (애플이 들어 있나)

**여기서 결론을 내지 않습니다.** 받은 것을 세고, 걸린 자리의 글자를 그대로
찍습니다. 규칙은 그것을 읽은 뒤에 짭니다.

왜 러너에서만 도는가
--------------------

개발 환경에서는 SEC 에 닿지 않습니다 — `www.sec.gov` · `data.sec.gov` 둘 다
프록시가 끊습니다(`000`/403, 여러 번 실측). 러너에서는 됩니다.

**아티팩트도 개발 환경에서 못 받습니다**(내려받기 주소가 blob.core.windows.net
이고 프록시가 403). 로그는 읽을 수 있으므로 **핵심은 로그에도 찍습니다** —
그러면 사용자가 파일을 받아 건네줄 필요가 없습니다. `probe_sec.py` 가 같은
이유로 같은 일을 합니다.

비밀값
------

    저장소 Settings → Secrets and variables → Actions
      SEC_CONTACT   SEC 에 밝힐 연락처 메일 주소

**없으면 종료코드 1 로 끝냅니다.** 손으로 돌리는 것은 "되는지 확인해 달라"는
뜻이라, 조용히 넘어가면 **초록불인데 아무것도 안 받아온** 상태가 됩니다.

저장 위치: scripts/probe_annual.py
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

OUT_DIR = "annual-probe"

# SEC 는 초당 10건을 넘지 말라고 합니다. 이 정찰은 수십 건 안쪽이라
# 넉넉히 띄워도 상관없습니다.
PAUSE = 0.25

# 한 파일이 이보다 크면 받지 않고 크기만 적습니다.
MAX_BYTES = 12 * 1024 * 1024

# XBRL 이 만든 낱장 보고서 중 받아 볼 것. **태그 이름을 짐작하지 않습니다** —
# 목차(FilingSummary.xml)가 주는 이름으로 고릅니다.
REPORT_HINT = re.compile(r"invest|equit|securit|fair value|cost", re.I)
# `Cybersecurity` 가 `securit` 으로 걸립니다. 첫 실행에서 실제로 걸려 받아 볼
# 자리를 한 칸 잡아먹었습니다(run 35881516841).
REPORT_SKIP = re.compile(r"cybersecurit", re.I)
# 그중에서도 **먼저** 열어 볼 것. 첫 실행이 알려 준 이름 그대로입니다 —
# 10-K 도 10-Q 도 `Investments in equity securities` 였습니다.
WANT_DEFAULT = "equity securit"

# 본문에서 취득원가 자리를 찾는 말. 넓게 걸고, 걸린 자리의 글자를 그대로 찍습니다.
COST_HINT = re.compile(r"\bcost\b|cost basis|amortized cost", re.I)


def ua(contact):
    """SEC 가 요구하는 형식: 누가 쓰는지 + 연락처."""
    return f"itpaidoff.com annual-report cost probe ({contact})"


def get(url, contact, tries=3):
    """한 번 받아서 기록을 돌려줍니다. HTTP 오류로 죽지 않습니다."""
    rec = {"url": url, "ok": False, "status": None, "bytes": 0, "error": None}
    body = b""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua(contact),
                "Accept": "application/json,text/html,application/xml,*/*",
                # gzip 을 요청하면 urllib 이 풀어 주지 않습니다. 이 저장소가
                # 실제로 한 번 여기서 틀렸습니다(`CLAUDE.md` 9-3).
                "Accept-Encoding": "identity",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                rec["ok"] = True
                rec["status"] = r.status
            break
        except urllib.error.HTTPError as e:            # noqa: PERF203
            rec["status"] = e.code
            rec["error"] = f"HTTP {e.code} {e.reason}"
            # 403 은 User-Agent 를 거절한 것이라 다시 걸어도 같습니다.
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                time.sleep(3.0 * (i + 1))
                continue
            break
        except Exception as e:                         # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    else:
        rec["error"] = f"{type(last).__name__}: {last}"
    rec["bytes"] = len(body)
    rec["_body"] = body
    time.sleep(PAUSE)
    return rec


def safe(name):
    """목차가 준 이름을 그대로 경로에 쓰지 않습니다."""
    name = name.replace("\\", "/").lstrip("/")
    if ".." in name.split("/"):
        return name.replace("/", "_")
    return name


def save(rec, name):
    """원본을 그대로 저장합니다. 아티팩트로 올라가는 것이 이것입니다."""
    path = os.path.join(OUT_DIR, safe(name))
    os.makedirs(os.path.dirname(path) or OUT_DIR, exist_ok=True)
    with open(path, "wb") as f:
        f.write(rec.get("_body", b""))
    out = {k: v for k, v in rec.items() if k != "_body"}
    out["saved"] = path
    return out


def text_of(body):
    """태그를 걷어 낸 글자. **해석이 아니라 눈으로 보려는 것입니다.**"""
    txt = body.decode("utf-8", "replace")
    txt = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", txt)
    txt = re.sub(r"(?i)</t[dh]>", " │ ", txt)      # 칸 경계를 남깁니다
    txt = re.sub(r"(?i)</tr>", "\n", txt)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    txt = re.sub(r"[ \t ]+", " ", txt)
    # **빈 칸이 줄을 길게 만듭니다.** 버크셔 표는 칸 사이에 빈 칸을 잔뜩
    # 끼워 넣어서, 첫 실행에서 취득원가 줄이 글자 수 제한에 걸려 통째로
    # 빠졌습니다. 이어지는 칸 경계를 하나로 줄입니다.
    txt = re.sub(r"(?:\│[ ]*){2,}", "│ ", txt)
    return re.sub(r"\n{2,}", "\n", txt)


def hits(txt, names, limit=40):
    """보유 종목 이름과 `cost` 가 **같은 줄**에 있는 자리를 그대로 모읍니다.

    이것이 이 정찰의 핵심 산출입니다. 숫자를 뽑아내지 않고 **줄을 통째로**
    남깁니다 — 열이 몇 개인지, 단위가 백만인지, 연도가 둘인지를 사람이 봐야
    합니다."""
    out = []
    for line in txt.splitlines():
        s = line.strip()
        if len(s) < 8 or len(s) > 1200:
            continue
        who = [n for n in names if n in s.upper()]
        if who and COST_HINT.search(s):
            out.append({"line": s, "names": who})
        elif who and re.search(r"\$?\s?\d[\d,]{2,}", s) and "│" in s:
            # 이름과 큰 수가 한 줄에 있고 표의 칸 경계가 보이는 자리.
            # `cost` 는 표 머리글에만 있을 수 있습니다.
            out.append({"line": s, "names": who})
        if len(out) >= limit:
            break
    return out


def census(body):
    """무엇이 들었는지만 셉니다. **파싱이 아닙니다.**"""
    txt = body.decode("utf-8", "replace")
    tags = {}
    for m in re.finditer(r"<\s*([A-Za-z_][\w.:-]*)", txt):
        t = m.group(1).split(":")[-1]
        tags[t] = tags.get(t, 0) + 1
    return {"tables": tags.get("table", 0) + tags.get("TABLE", 0),
            "tag_kinds": len(tags),
            "cost_words": len(COST_HINT.findall(txt))}


def filings_of(sub, forms):
    """제출 목록에서 그 서식들을 찾습니다(최신이 앞).

    `filings.recent` 만 봅니다. 더 오래된 것은 `filings.files` 에 쪼개져
    있고, 그 개수는 따로 찍습니다 — 10-K 는 해마다 한 건이라 최근 목록에
    여러 해가 들어 있습니다."""
    recent = (sub.get("filings") or {}).get("recent") or {}
    all_forms = recent.get("form") or []
    out = []
    for i, f in enumerate(all_forms):
        if f not in forms:
            continue
        out.append({k: (recent.get(k) or [None] * len(all_forms))[i]
                    for k in ("form", "filingDate", "reportDate",
                              "accessionNumber", "primaryDocument", "size")})
    return out


def one_filing(cik_int, filing, contact, names, show, notes, want, deep, light):
    """한 건의 제출 폴더를 훑습니다.

    **파일 이름을 짐작하지 않습니다** — 목차(index.json)가 주는 이름만 씁니다.
    받는 것은 셋입니다: 본문(A), XBRL 이 만든 낱장 보고서 목차(B),
    그 목차에서 이름이 걸리는 낱장들(B-2)."""
    acc = re.sub(r"\D", "", filing["accessionNumber"] or "")
    tag = f"{filing['form'].replace('/', '-')}-{filing['reportDate']}"
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}"
    print(f"\n[{tag}] {filing['filingDate']} 제출 · {filing['reportDate']} 기준")
    print(f"    {base}/index.json")

    item = {"form": filing["form"], "filed": filing["filingDate"],
            "period": filing["reportDate"], "accession": filing["accessionNumber"],
            "files": [], "reports": [], "hits": []}

    rec = get(f"{base}/index.json", contact)
    notes.append(save(rec, f"{tag}/index.json"))
    if not rec["ok"]:
        print(f"    목차를 못 받았습니다 — {rec['error']}")
        item["index_error"] = rec["error"]
        return item
    try:
        items = json.loads(rec["_body"])["directory"]["item"]
    except Exception as e:                             # noqa: BLE001
        print(f"    목차를 읽지 못했습니다 — {e}")
        item["index_error"] = str(e)
        return item
    item["files"] = [{"name": it.get("name"), "bytes": int(it.get("size") or 0)}
                     for it in items]
    print(f"    파일 {len(items)}개")

    # ── A. 본문 ────────────────────────────────────────────────
    primary = filing.get("primaryDocument") or ""
    size = next((f["bytes"] for f in item["files"] if f["name"] == primary), 0)
    if light:
        # 여러 해를 훑을 때 10MB 본문을 해마다 받을 이유가 없습니다.
        # 답은 XBRL 낱장에 있고, 낱장은 수십 KB 입니다.
        print(f"    A 본문 {primary} {size:,}b — 가벼운 훑기라 건너뜁니다")
        item["primary"] = {"name": primary, "bytes": size, "skipped": "light"}
    elif primary and size <= MAX_BYTES:
        r = get(f"{base}/{primary}", contact)
        notes.append(save(r, f"{tag}/{safe(primary)}"))
        if r["ok"]:
            cen = census(r["_body"])
            item["primary"] = {"name": primary, "bytes": r["bytes"], **cen}
            found = hits(text_of(r["_body"]), names)
            item["hits"] = found
            print(f"    A 본문 {primary} {r['bytes']:,}b · 표 {cen['tables']}개"
                  f" · 'cost' {cen['cost_words']}번 · 이름 걸린 줄 {len(found)}개")
            for h in found[:show]:
                print(f"        {h['line'][:300]}")
        else:
            print(f"    A 본문을 못 받았습니다 — {r['error']}")
    elif primary:
        print(f"    A 본문 {primary} {size:,}b — 큽니다. 크기만 적습니다.")
        item["primary"] = {"name": primary, "bytes": size, "skipped": "too big"}

    # ── B. XBRL 이 만든 낱장 보고서 ────────────────────────────
    # **이 목차가 B 질문의 답입니다.** 여기 실린 보고서는 XBRL 태그에서
    # 만들어진 것이므로, 취득원가 표가 여기 있으면 태그돼 있다는 뜻입니다.
    if any(f["name"] == "FilingSummary.xml" for f in item["files"]):
        r = get(f"{base}/FilingSummary.xml", contact)
        notes.append(save(r, f"{tag}/FilingSummary.xml"))
        if r["ok"]:
            body = r["_body"].decode("utf-8", "replace")
            reports = re.findall(
                r"<Report[^>]*>(.*?)</Report>", body, re.S | re.I)
            named = []
            for rep in reports:
                short = re.search(r"<ShortName>(.*?)</ShortName>", rep, re.S | re.I)
                fname = re.search(r"<HtmlFileName>(.*?)</HtmlFileName>", rep, re.S | re.I)
                if short:
                    named.append({"name": html.unescape(short.group(1)).strip(),
                                  "file": (fname.group(1).strip() if fname else "")})
            item["reports"] = named
            picked = [n for n in named
                      if n["file"] and REPORT_HINT.search(n["name"])
                      and not REPORT_SKIP.search(n["name"])]
            # **이름은 전부 찍습니다.** 스물몇 줄이면 아무것도 아니고, 이 목록이
            # 곧 어느 낱장을 열어야 하는지의 지도입니다. 첫 실행에서 절반만
            # 찍는 바람에 `(Details)` 낱장들이 목록에서 잘렸습니다.
            print(f"    B 낱장 보고서 {len(named)}개 · 이름이 걸린 것 {len(picked)}개")
            for n in picked:
                print(f"        {n['file']:<12} {n['name']}")
            # ── B-2. 걸린 낱장을 실제로 받아 봅니다 (작습니다) ──
            # 먼저 열 것을 앞으로 당깁니다 — 첫 실행이 알려 준 이름입니다.
            hit = re.compile(re.escape(want), re.I) if want else None
            order = ([n for n in picked if hit and hit.search(n["name"])]
                     + [n for n in picked if not (hit and hit.search(n["name"]))])
            for n in order[:show]:
                rr = get(f"{base}/{n['file']}", contact)
                notes.append(save(rr, f"{tag}/{safe(n['file'])}"))
                if not rr["ok"]:
                    continue
                lines = [l.strip() for l in text_of(rr["_body"]).splitlines()
                         if l.strip()]
                n["bytes"] = rr["bytes"]
                n["lines"] = len(lines)
                print(f"        ── {n['file']} ({n['name']}) {rr['bytes']:,}b · {len(lines)}줄")
                for l in lines[:40]:
                    print(f"           {l[:400]}")
                # **여기가 핵심입니다.** 앞머리만 찍으면 표 앞의 설명 문단에서
                # 끝납니다(첫 실행이 그랬습니다). 보유 종목 이름이 걸린 줄을
                # 따로 모아 찍습니다 — 취득원가 표가 있다면 그 줄들입니다.
                marked = [l for l in lines if any(x in l.upper() for x in names)]
                n["name_lines"] = len(marked)
                print(f"           ── 보유 종목 이름이 걸린 줄 {len(marked)}개")
                for l in marked[:deep]:
                    print(f"           · {l[:400]}")
                # **표의 행 이름이 곧 답입니다.** 2차 실행에서 취득원가 표의
                # 행이 종목이 아니라 업종(`Banks, insurance and finance`)이라는
                # 것이 여기서 드러났습니다. 우리 보유 이름과 안 맞아도 보이게
                # `[Member]` 줄을 따로 찍습니다 — 그것이 XBRL 의 행 차원입니다.
                mem = [l for l in lines if "[Member]" in l or "Axis=" in l]
                n["member_lines"] = len(mem)
                if mem:
                    print(f"           ── 표의 행 이름([Member]) {len(mem)}개")
                    for l in mem[:deep]:
                        print(f"           # {l[:300]}")
        else:
            print(f"    B FilingSummary.xml 을 못 받았습니다 — {r['error']}")
    else:
        print("    B FilingSummary.xml 이 목차에 없습니다 (XBRL 낱장 없음)")
    return item


def main():
    ap = argparse.ArgumentParser(
        description="연차보고서 취득원가 정찰 — 받아서 재고 원본을 저장합니다")
    ap.add_argument("--slug", default="berkshire",
                    help="data/titans/<slug>.json · investors.json 의 이름")
    ap.add_argument("--forms", default="10-K,10-Q",
                    help="받을 서식. 10-Q 는 '얼마나 자주 잴 수 있나'의 답입니다")
    ap.add_argument("--count", type=int, default=1,
                    help="서식마다 최근 몇 건을 받을지")
    ap.add_argument("--show", type=int, default=8,
                    help="로그에 찍을 줄 수 (아티팩트를 개발 환경에서 못 받습니다)")
    ap.add_argument("--want", default=WANT_DEFAULT,
                    help="이 이름이 든 낱장을 먼저 엽니다 (빈 칸이면 순서대로)")
    ap.add_argument("--lines", type=int, default=80,
                    help="낱장에서 이름이 걸린 줄을 몇 개까지 찍을지")
    ap.add_argument("--light", action="store_true",
                    help="10MB 본문을 건너뛰고 XBRL 낱장만 봅니다 (여러 해를 훑을 때)")
    ap.add_argument("--cik", default="", help="registry 에 없을 때만")
    a = ap.parse_args()

    contact = (os.environ.get("SEC_CONTACT") or "").strip()
    if not contact:
        print("정찰을 할 수 없습니다 — 비밀값 SEC_CONTACT 가 없습니다.")
        print("  SEC 는 이름 없는 요청을 거절합니다. 연락처 메일 주소를 밝혀야 합니다.")
        print("  저장소 Settings → Secrets and variables → Actions 에서 넣어 주세요.")
        print("  (이 저장소는 공개라 코드에 주소를 박으면 긁힙니다. 그래서 비밀값입니다.)")
        return 1

    # CIK 은 공시책이 아니라 **registry** 에 있습니다. 여기에 또 적으면
    # 두 벌이 되어 갈라집니다. 읽기만 하고 고치지 않습니다.
    cik = re.sub(r"\D", "", a.cik)
    if not cik:
        with open(os.path.join("data", "titans", "investors.json"), encoding="utf-8") as f:
            reg = json.load(f)
        for inv in reg.get("investors") or []:
            if inv.get("slug") == a.slug:
                cik = re.sub(r"\D", "", str(inv.get("cik") or ""))
                break
    if not cik:
        print(f"{a.slug} 의 CIK 을 registry 에서 못 찾았습니다. --cik 으로 주세요.")
        return 1
    cik, cik_int = cik.zfill(10), str(int(cik))

    # 대조할 상대는 **우리 자료의 지금 보유 종목**입니다. 이름을 손으로
    # 적지 않습니다 — 분기마다 바뀌고, 사람이 붙어야 하는 표는 결국 낡습니다.
    book_path = os.path.join("data", "titans", f"{a.slug}.json")
    if not os.path.exists(book_path):
        print(f"{book_path} 가 없습니다.")
        return 1
    with open(book_path, encoding="utf-8") as f:
        book = json.load(f)
    quarters = sorted(book.get("quarters") or [], key=lambda q: q["period"])
    if not quarters:
        print("공시책에 분기가 없습니다.")
        return 1
    last = quarters[-1]
    names = sorted({(h["name"] or "").upper().split()[0]
                    for h in last["holdings"] if len(h["name"] or "") > 3})
    names = [n for n in names if len(n) >= 4]

    print(f"{a.slug} · CIK {cik} · 우리 최신 분기 {last['period']}"
          f" · 보유 {len(last['holdings'])}줄")
    print(f"찾을 이름 {len(names)}개: {', '.join(names[:12])}"
          + (" …" if len(names) > 12 else ""))
    print("해석하지 않고 재기만 합니다. 대조 규칙은 이 결과를 읽은 뒤에 짭니다.")

    os.makedirs(OUT_DIR, exist_ok=True)
    notes = []
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"\n[목록] {url}")
    rec = get(url, contact)
    notes.append(save(rec, "submissions.json"))
    print(f"    {rec['status']}  {rec['bytes']:,} bytes  {rec['error'] or ''}")
    if not rec["ok"]:
        print("    → 여기서 멈춥니다. 403 이면 SEC 가 User-Agent 를 거절한 것입니다.")
        return 1
    sub = json.loads(rec["_body"])

    # 제출 목록에 어떤 서식이 있는지 공짜로 셉니다. **주주 서한(ARS)이
    # 따로 제출돼 있는지**가 여기서 드러납니다 — 취득원가 표가 10-K 에 없다면
    # 다음으로 볼 곳이 거기입니다.
    kinds = {}
    for name in ((sub.get("filings") or {}).get("recent") or {}).get("form") or []:
        kinds[name] = kinds.get(name, 0) + 1
    # **자르지 않습니다.** 3차 실행에서 18개로 잘라 찍는 바람에 "주주 서한(ARS)이
    # 아예 없다"를 확정하지 못했습니다 — 건수가 적은 서식이 잘린 자리에 숨습니다.
    print("    서식별 건수: " + " · ".join(
        f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])))

    forms = [f.strip() for f in a.forms.split(",") if f.strip()]
    found = filings_of(sub, set(forms))
    older = len((sub.get("filings") or {}).get("files") or [])
    print(f"    최근 목록에서 {'/'.join(forms)} {len(found)}건"
          f" · 더 오래된 목록 파일 {older}개")

    result = []
    for form in forms:
        for filing in [f for f in found if f["form"] == form][:a.count]:
            result.append(one_filing(cik_int, filing, contact, names, a.show, notes,
                                     a.want, a.lines, a.light))

    summary = {
        "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "slug": a.slug, "cik": cik,
        "user_agent": ua("<SEC_CONTACT>"),   # 주소는 어디에도 적지 않습니다
        "our_latest_quarter": last["period"], "looked_for": names,
        "note": "셈과 원문뿐입니다. 대조 규칙은 이 결과를 읽은 뒤에 사람이 정합니다.",
        "filings": result, "fetched": notes,
    }
    with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    bad = [n for n in notes if not n.get("ok")]
    print(f"\n받은 파일 {len(notes)}개 · 못 받은 것 {len(bad)}개")
    print(f"원본과 셈은 {OUT_DIR}/ 에 있습니다. 아티팩트로 올라갑니다.")
    # 하나도 못 받았을 때만 실패입니다. "찾는 표가 없더라"는 **고장이 아니라
    # 답**이고, 그것으로 빨간불을 켜면 진짜 고장이 묻힙니다(`CLAUDE.md` 6-2).
    return 1 if len(bad) == len(notes) else 0


if __name__ == "__main__":
    sys.exit(main())
