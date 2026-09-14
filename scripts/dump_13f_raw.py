"""
대가들의 선택 — 2013년 이전 13F 원본을 통째로 내려받는다 (한 번만 쓰는 것)

**이것은 파이프라인이 아닙니다.** 한 번 돌리고 버릴 심부름꾼입니다.

왜 필요한가. 2013년 중반 이전 13F 는 폴더에 XML 이 없습니다 — EDGAR 가
그때는 XML 을 안 받았고, 텍스트 문서입니다. 그 58분기(1998-12-31 ~
2013-03-31)를 되살리면 **2008년이 들어옵니다.** "그 선택이 어떻게 됐나"를
보여 주는 사이트에서 가장 값진 구간입니다.

그런데 그 문서를 어시스턴트가 볼 수가 없습니다.

    SEC 는 개발 환경에서 막혀 있다        → 직접 못 받는다
    58건 × 90KB ≈ 5MB                    → 실행 로그로 읽기엔 너무 크다
    아티팩트는 blob.core.windows.net     → 프록시가 403 으로 끊는다

그래서 **저장소의 임시 브랜치에 원본을 그대로 올립니다.** 그러면 어시스턴트가
그 브랜치를 받아서 여기서 직접 읽고, 형식에 맞춰 한 번에 정리할 수 있습니다.
클릭하고 로그 기다리는 왕복이 사라집니다.

13F 는 미국 정부 저작물이라 퍼블릭 도메인입니다. 공개 저장소에 둬도 됩니다.

**정리가 끝나면 이 스크립트도, 그 브랜치도 지웁니다.** 남겨 두면 다음 세션이
파이프라인인 줄 알고 붙듭니다.

정정 공시(13F-HR/A)도 함께 받습니다 — 100건 중 90건쯤이 이 구간이라,
어차피 그 모양도 봐야 합니다.

저장 위치: scripts/dump_13f_raw.py
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_13f import CIK, FORM, MAX_BYTES, get, list_filings   # noqa: E402


def dump(cik_int: str, f: dict, contact: str, out: str) -> dict:
    """한 건의 폴더를 통째로 내려 저장합니다. 고르지 않고 다 받습니다."""
    acc = re.sub(r"\D", "", f["accession"])
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}"
    rec = {"period": f["period"], "filed": f["filed"], "form": f.get("form", FORM),
           "accession": f["accession"], "files": []}

    body = get(f"{base}/index.json", contact)
    if not body:
        rec["error"] = "index.json 을 못 받음"
        return rec

    d = os.path.join(out, f"{f['period']}_{f['accession']}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.json"), "wb") as fh:
        fh.write(body)

    for it in ((json.loads(body).get("directory") or {}).get("item") or []):
        name = (it.get("name") or "").replace("\\", "/").lstrip("/")
        if not name or ".." in name.split("/"):
            continue
        try:
            size = int(it.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        # 화면용 HTML 은 건너뜁니다. EDGAR 가 사람 보라고 만든 껍데기라
        # 자료가 아니고, 58건 × 8KB 면 브랜치만 무거워집니다.
        if name.lower().endswith((".htm", ".html")):
            continue
        if size > MAX_BYTES:
            rec["files"].append({"name": name, "size": size, "skipped": "too large"})
            continue
        b = get(f"{base}/{name}", contact)
        if b is None:
            rec["files"].append({"name": name, "size": size, "skipped": "실패"})
            continue
        p = os.path.join(d, os.path.basename(name))
        with open(p, "wb") as fh:
            fh.write(b)
        rec["files"].append({"name": name, "bytes": len(b)})
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(
        description="2013년 이전 13F 원본을 통째로 내려받는다 (한 번만)")
    ap.add_argument("--out", default="sec-raw", help="저장할 폴더")
    ap.add_argument("--limit", type=int, default=0, help="시험용으로 앞 N건만")
    a = ap.parse_args()

    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        print("받을 수 없습니다 — 비밀값 SEC_CONTACT 가 없습니다.")
        print("  저장소 Settings → Secrets and variables → Actions 에 넣어 주세요.")
        return 1

    cik_int = str(int(CIK))
    filings, amends = list_filings(contact)
    if not filings:
        print("제출 목록을 받지 못했습니다. 아무것도 쓰지 않습니다.")
        return 1

    # XML 이 있는 분기는 이미 fetch_13f.py 가 처리합니다. 여기서는
    # **XML 이 없는 것만** 받습니다 — 그 판정은 목차를 봐야 알 수 있으므로
    # 일단 다 훑되, 2013-06-30 이후는 건너뜁니다(실측 경계).
    XML_FROM = "2013-06-30"
    todo = [dict(x, form=FORM) for x in filings if x["period"] < XML_FROM]
    todo += [dict(x, form=FORM + "/A") for x in amends if x["period"] < XML_FROM]
    todo.sort(key=lambda x: (x["period"], x["filed"]))
    if a.limit:
        todo = todo[:a.limit]

    print(f"내려받을 것 {len(todo)}건 "
          f"(원본 {sum(1 for x in todo if x['form'] == FORM)} · "
          f"정정 {sum(1 for x in todo if x['form'] != FORM)})")
    print(f"구간 {todo[0]['period']} ~ {todo[-1]['period']}")

    os.makedirs(a.out, exist_ok=True)
    recs, total = [], 0
    for i, f in enumerate(todo, 1):
        r = dump(cik_int, f, contact, a.out)
        recs.append(r)
        got = sum(x.get("bytes", 0) for x in r["files"])
        total += got
        print(f"  [{i:>3}/{len(todo)}] {r['period']}  {r['form']:<9} "
              f"{r['accession']}  파일 {len(r['files'])}개  {got:>8,} bytes"
              f"{'  ← ' + r['error'] if r.get('error') else ''}")

    with open(os.path.join(a.out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"cik": CIK, "count": len(recs), "bytes": total,
                   "filings": recs}, fh, ensure_ascii=False, indent=2)
    print(f"\n{a.out}/  {len(recs)}건 · 합계 {total:,} bytes")
    print("이제 이 폴더를 브랜치로 올립니다. 어시스턴트가 받아서 직접 읽습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
