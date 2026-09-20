"""
대가들의 선택 — 13F 정정 공시(13F-HR/A) 정찰(probe)

**이 스크립트는 파서가 아닙니다.** 받아서 재고 원본을 그대로 저장할 뿐입니다.
정정을 어떻게 병합할지는 여기서 정하지 않습니다 — 이것을 읽은 뒤에 사람이 정합니다.
`probe_sec.py` 와 같은 요령이고, 같은 이유로 따로 있습니다.

무엇을 알아내려는 것인가
------------------------

정정에는 두 모양이 섞여 있습니다.

    전체 재작성   분기 전체를 다시 적어 보냄 → 원본을 **갈아끼워야** 합니다
    추가 공개분   비공개였던 몫만 뒤늦게 적어 보냄 → 원본에 **더해야** 합니다

**둘을 반대로 처리하면 종목이 두 배가 되거나 통째로 사라집니다.** 그래서
`fetch_13f.py` 는 지금까지 정정을 일부러 안 받고 "있다"고만 알려 왔습니다.

13F XML 표지에 이 구분을 적는 항목이 있는지 **원문을 받아 확인하는 것**이
이 정찰의 전부입니다. 있으면 그것을 쓰고, 없으면 다른 근거를 찾아야 합니다.
**접수 시차로 짐작해서 규칙을 만들지 않습니다** — 이 저장소는 그 자리에서
이미 두 번 틀렸습니다(gzip 미해제, OpenFIGI 응답 짐작 — `CLAUDE.md` 9-3).

왜 러너에서만 도는가
--------------------

개발 환경에서는 SEC 에 닿지 않습니다. 실측으로 `www.sec.gov:443` ·
`data.sec.gov:443` 둘 다 프록시가 끊습니다(2026-09-20 재확인, `000`).
러너에서는 됩니다.

무엇을 재는가 (전부 셈이고, 해석이 아닙니다)
--------------------------------------------

    A  분기 목록에서 정정이 달린 분기를 고릅니다 (XML 시대만)
    B  원본과 정정 각각의 폴더 목차(index.json)를 받습니다
    C  목차가 주는 이름 그대로 XML 을 받습니다 — 파일 이름을 짐작하지 않습니다
    D  태그 이름을 **전부** 셉니다 (상위 몇 개만 자르지 않습니다 —
       표지의 드문 항목 하나를 찾는 중이라 잘라 내면 그게 사라집니다)
    E  잎 항목 중 이름에 amend·conf·report·period 가 들어간 것의 **글자 그대로의 값**
    F  정보표 줄 수와 value·shares 합계

E 와 F 가 핵심입니다. E 는 "표지가 무엇이라고 적어 뒀나", F 는 "줄 수와 금액이
원본과 같은 규모인가 아니면 일부뿐인가" — 둘을 나란히 놓으면 구분이 드러납니다.
**드러난 것을 여기서 결론으로 적지는 않습니다.**

비밀값
------

    저장소 Settings → Secrets and variables → Actions
      SEC_CONTACT   SEC 에 밝힐 연락처 메일 주소

**없으면 종료코드 1 로 끝냅니다.** `notify.py --test` · `probe_sec.py` 와 같은
이유입니다 — 손으로 돌리는 것은 "되는지 확인해 달라"는 뜻이라, 조용히 넘어가면
**초록불인데 아무것도 안 받아온** 상태가 됩니다.

저장 위치: scripts/probe_amendments.py
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

OUT_DIR = "amend-probe"

# SEC 는 초당 10건을 넘지 말라고 합니다. 넉넉히 띄웁니다 — 이 정찰은
# 스무 건 안쪽이라 느려져도 상관없습니다.
PAUSE = 0.25

# XML 시대의 경계. 저장소 실측으로 1998-12-31 ~ 2013-03-31 이 텍스트였고
# 그 뒤가 XML 입니다(`fetch_13f.py` 189행). 텍스트 시대 정정은 사용자가
# **투자자별 일회성 변환**으로 확정했으므로 이 정찰의 대상이 아닙니다
# (`CLAUDE.md` 9-3-1). 반복 자동화·공통 유지 파서를 만들지 않습니다.
XML_FROM = "2013-04-01"

# 한 파일이 이보다 크면 받지 않고 크기만 적습니다.
MAX_BYTES = 8 * 1024 * 1024


def ua(contact):
    """SEC 가 요구하는 형식: 누가 쓰는지 + 연락처."""
    return f"itpaidoff.com 13F amendment probe ({contact})"


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
            with urllib.request.urlopen(req, timeout=45) as r:
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


TAG = re.compile(rb"<\s*([A-Za-z_][\w.:-]*)")
# 여는 태그 · 값 · 닫는 태그가 한 줄에 있는 잎 항목. 13F XML 은 이 모양입니다.
LEAF = re.compile(rb"<\s*([A-Za-z_][\w.:-]*)\s*>\s*([^<>]{1,200}?)\s*<\s*/")

# 표지에서 찾는 것. **이름을 하나로 못박지 않습니다** — 실제 항목 이름이
# 짐작과 다를 수 있으므로 넓게 걸고, 걸린 것의 값을 글자 그대로 적습니다.
WANTED = re.compile(r"amend|conf|report|period|restat|holding", re.I)


def localname(tag):
    """`ns1:amendmentType` → `amendmentType`."""
    return tag.split(":")[-1]


def census(body):
    """무엇이 들었는지만 셉니다. **파싱이 아닙니다.**"""
    out = {}
    counts = {}
    for m in TAG.finditer(body):
        t = localname(m.group(1).decode("ascii", "replace"))
        counts[t] = counts.get(t, 0) + 1
    # **자르지 않습니다.** 표지의 드문 항목 하나를 찾는 중입니다.
    out["tags"] = dict(sorted(counts.items()))
    out["tag_kinds"] = len(counts)

    # 이름이 걸리는 잎 항목의 값을 글자 그대로. 같은 이름이 여러 번이면
    # 서로 다른 값만 모읍니다(정보표 안에서 되풀이되는 것을 줄이려고).
    seen = {}
    for m in LEAF.finditer(body):
        name = localname(m.group(1).decode("ascii", "replace"))
        if not WANTED.search(name):
            continue
        val = m.group(2).decode("utf-8", "replace").strip()
        vals = seen.setdefault(name, [])
        if val not in vals and len(vals) < 8:
            vals.append(val)
    out["marked_leaves"] = seen
    return out


NUM = re.compile(rb"<\s*(?:[\w.-]+:)?(value|sshPrnamt)\s*>\s*([0-9,.]+)\s*<")


def table_size(body):
    """정보표의 규모만 잽니다 — 줄 수와 합계.

    **이것이 구분의 절반입니다.** 정정의 줄 수·금액이 원본과 같은 규모면
    통째로 다시 쓴 것이고, 몇 줄뿐이면 빠진 몫만 더한 것입니다.
    다만 **여기서 그렇게 결론 내지 않습니다.** 숫자만 적습니다."""
    rows = len(re.findall(rb"<\s*(?:[\w.-]+:)?infoTable\s*>", body))
    total = {"value": 0.0, "sshPrnamt": 0.0}
    for m in NUM.finditer(body):
        key = m.group(1).decode()
        try:
            total[key] += float(m.group(2).decode().replace(",", ""))
        except ValueError:
            pass
    return {"infoTable_rows": rows,
            "sum_value": total["value"], "sum_shares": total["sshPrnamt"]}


def one_filing(cik_int, accession, contact, tag, notes):
    """한 건의 폴더를 훑습니다. **파일 이름을 짐작하지 않습니다** —
    목차(index.json)가 주는 이름만 씁니다."""
    acc = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}"
    print(f"  [{tag}] {accession}  {base}/index.json")

    rec = get(f"{base}/index.json", contact)
    step = save(rec, f"{tag}/index.json")
    notes.append(step)
    if not rec["ok"]:
        print(f"      목차를 못 받았습니다 — {rec['error']}")
        return {"accession": accession, "index_error": rec["error"], "files": []}

    try:
        items = json.loads(rec["_body"])["directory"]["item"]
    except Exception as e:                             # noqa: BLE001
        print(f"      목차를 읽지 못했습니다 — {e}")
        return {"accession": accession, "index_error": str(e), "files": []}

    got = []
    for it in items:
        name = it.get("name") or ""
        size = int(it.get("size") or 0)
        if not name.lower().endswith((".xml", ".txt")):
            continue
        if size > MAX_BYTES:
            print(f"      {name} {size:,} bytes — 큽니다. 크기만 적습니다.")
            got.append({"name": name, "bytes": size, "skipped": "too big"})
            continue
        r = get(f"{base}/{name}", contact)
        s = save(r, f"{tag}/{safe(name)}")
        notes.append(s)
        entry = {"name": name, "bytes": r["bytes"], "status": r["status"]}
        if r["ok"] and r["_body"]:
            entry.update(census(r["_body"]))
            entry.update(table_size(r["_body"]))
        got.append(entry)
        rows = entry.get("infoTable_rows", 0)
        marks = entry.get("marked_leaves") or {}
        print(f"      {name:<34} {r['bytes']:>8,}b  줄 {rows:>4}"
              + (f"  표시항목 {len(marks)}종" if marks else ""))
        for k, v in sorted(marks.items()):
            print(f"          {k} = {v}")
    return {"accession": accession, "files": got}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="berkshire",
                    help="data/titans/<slug>.json 의 이름")
    ap.add_argument("--since", default=XML_FROM,
                    help=f"이 기준일 이후 분기만 (기본 {XML_FROM} — XML 시대)")
    ap.add_argument("--limit", type=int, default=0,
                    help="분기를 이 개수까지만 (0 이면 전부)")
    ap.add_argument("--cik", default="",
                    help="registry 에 없을 때만. 보통은 비워 둡니다")
    a = ap.parse_args()

    contact = (os.environ.get("SEC_CONTACT") or "").strip()
    if not contact:
        print("SEC_CONTACT 비밀값이 없습니다. SEC 는 이름 없는 요청을 거절합니다.\n"
              "  저장소 Settings → Secrets and variables → Actions 에 넣으세요.\n"
              "  조용히 넘어가면 초록불인데 아무것도 안 받아온 상태가 됩니다.")
        return 1

    book_path = os.path.join("data", "titans", f"{a.slug}.json")
    if not os.path.exists(book_path):
        print(f"{book_path} 가 없습니다.")
        return 1
    with open(book_path, encoding="utf-8") as f:
        book = json.load(f)

    # CIK 은 공시책이 아니라 **registry** 에 있습니다. 투자자 목록이 하나라는
    # 구조를 그대로 따릅니다 — 여기에 CIK 을 또 적으면 두 벌이 되어 갈라집니다.
    # 읽기만 하고 고치지 않습니다(그 파일은 Codex 것입니다).
    cik = (a.cik or "").strip()
    if not cik:
        reg_path = os.path.join("data", "titans", "investors.json")
        with open(reg_path, encoding="utf-8") as f:
            reg = json.load(f)
        for inv in reg.get("investors") or []:
            if inv.get("slug") == a.slug:
                cik = str(inv.get("cik") or "").strip()
                break
    if not cik.isdigit():
        print(f"{a.slug} 의 CIK 을 registry 에서 못 찾았습니다. --cik 으로 주세요.")
        return 1
    cik_int = str(int(cik))

    quarters = [q for q in book.get("quarters") or []
                if q.get("amended_by") and q.get("period", "") >= a.since]
    quarters.sort(key=lambda q: q["period"])
    if a.limit:
        quarters = quarters[:a.limit]

    total_amend = sum(len(q["amended_by"]) for q in quarters)
    print(f"{a.slug} · CIK {cik}")
    print(f"{a.since} 이후 정정이 달린 분기 {len(quarters)}개 · 정정 {total_amend}건")
    print("원본과 정정을 나란히 받습니다. 해석하지 않고 재기만 합니다.\n")
    if not quarters:
        print("받을 것이 없습니다.")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    notes, result = [], []
    for q in quarters:
        print(f"{q['period']}  원본 냄 {q.get('filed')}")
        item = {"period": q["period"], "filed": q.get("filed"),
                "stored_total": q.get("total"), "stored_lines": q.get("lines"),
                "stored_holdings": len(q.get("holdings") or [])}
        item["original"] = one_filing(cik_int, q["accession"], contact,
                                      f"{q['period']}/original", notes)
        item["amendments"] = [
            one_filing(cik_int, acc, contact, f"{q['period']}/amend-{i+1}", notes)
            for i, acc in enumerate(q["amended_by"])]
        result.append(item)
        print()

    summary = {
        "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "slug": a.slug, "cik": cik, "since": a.since,
        "quarters": len(quarters), "amendments": total_amend,
        "note": "셈만 적은 것입니다. 병합 규칙은 이 결과를 읽은 뒤에 사람이 정합니다.",
        "result": result, "fetched": notes,
    }
    with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    bad = [n for n in notes if not n.get("ok")]
    print(f"받은 파일 {len(notes)}개 · 못 받은 것 {len(bad)}개")
    print(f"원본과 셈은 {OUT_DIR}/ 에 있습니다. 아티팩트로 올라갑니다.")
    # 하나도 못 받았으면 실패로 끝냅니다 — 초록불인데 빈손이면 안 됩니다.
    return 1 if len(bad) == len(notes) else 0


if __name__ == "__main__":
    sys.exit(main())
