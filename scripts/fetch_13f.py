"""
대가들의 선택 — 등록된 투자자 한 명의 13F 공시를 JSON 으로 저장합니다.

`scripts/probe_sec.py` 가 정찰한 결과로 만든 것입니다. 세 번 돌려서
알아낸 것이 아래 셋이고, **셋 다 짐작했으면 틀렸을 자리**입니다.

  1. 보유 목록 파일 이름에 규칙이 없다
       2026-06-30  56757.xml
       2016-12-31  form13fInfoTable.xml
     이름을 박으면 한 분기는 되고 다음 분기에 깨진다. **목차(index.json)를
     읽어서 primary_doc.xml 이 아닌 XML 을 고른다.**
     제출 목록의 primaryDocument 를 따라가면 안 된다 — 그것은 사람 보라고
     만든 표지(xslForm13F_X02/...)이고 종목이 하나도 없다.

  2. 한 줄이 한 종목이 아니다
     같은 회사가 여러 관리 주체나 주식 종류 때문에 여러 줄로 나올 수 있다.
     공시의 tableEntryTotal(89)은 **줄 수**이지 종목 수가 아니다.
     cusip 으로 묶어서 더해야 실제 보유가 나온다.

  3. 금액 단위가 도중에 바뀌었다
       2026-06-30  금액÷주식수 = 45.95     → 달러
       2016-12-31  금액÷주식수 = 0.0467    → 천 달러 (×1000 하면 46.69)
     날짜를 외워서 박지 않는다. **매 분기 금액÷주식수의 중앙값을 재서**
     1 보다 작으면 천 달러로 보고 1000을 곱한다. 종목 50개의 중앙값이라
     한두 종목이 이상해도 흔들리지 않는다.

투자자·CIK·저장 파일은 data/titans/investors.json 에서 고릅니다.
금액은 전부 달러로 맞춰 둡니다.

정정 공시(13F-HR/A)는 받지 않습니다. 있는지 없는지만 로그에 알립니다 —
이유는 list_filings() 안에 적어 뒀습니다.

저장 위치: scripts/fetch_13f.py
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))
from titans.registry import one
from titans.sec import form_rows, get

OUT = "data/titans/berkshire.json"
# 정정 공시가 새로 뜨면 이 파일을 남깁니다. 워크플로가 이것을 보고 텔레그램을
# 보냅니다. **저장소에 커밋하지 않습니다** — 알림용 쪽지일 뿐입니다.
ALERT = "amend-alert.txt"

# 직접 실행과 기존 단위 검사의 기본값입니다. 자동 실행은 registry의 값을 넘깁니다.
CIK = "0001067983"
MANAGER_NAME = "Berkshire Hathaway Inc"
FORM = "13F-HR"
MAX_BYTES = 64 * 1024 * 1024


def local(tag: str) -> str:
    """`{네임스페이스}infoTable` → `infoTable`."""
    return tag.split("}")[-1]


def num(s: str | None) -> int:
    """숫자만 남겨서 정수로. 빈 값은 0."""
    if not s:
        return 0
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else 0


def rows_of(xml: bytes) -> list[dict]:
    """정보표에서 줄을 그대로 꺼냅니다. 묶지도 고치지도 않습니다."""
    out = []
    root = ET.fromstring(xml)
    for el in root.iter():
        if local(el.tag) != "infoTable":
            continue
        f = {}
        for kid in el.iter():
            k = local(kid.tag)
            if kid.text and kid.text.strip():
                f.setdefault(k, kid.text.strip())
        out.append({
            "name": f.get("nameOfIssuer", ""),
            "class": f.get("titleOfClass", ""),
            "cusip": (f.get("cusip", "") or "").upper(),
            "value": num(f.get("value")),
            "shares": num(f.get("sshPrnamt")),
            "type": f.get("sshPrnamtType", ""),     # SH(주식) / PRN(원금)
            "putCall": f.get("putCall", ""),        # 없는 분기가 대부분
        })
    return out


def unit_scale(rows: list[dict]) -> tuple[int, float]:
    """금액이 달러인지 천 달러인지 **재서** 정합니다.

    주식(SH)만 보고 금액÷주식수의 중앙값을 냅니다. 그것이 곧 주가여야
    하므로, 1 보다 작으면 금액이 천 달러 단위라는 뜻입니다."""
    r = [x["value"] / x["shares"] for x in rows
         if x["type"] == "SH" and x["shares"] > 0 and x["value"] > 0]
    if not r:
        return 1, 0.0
    m = median(r)
    return (1000, m) if m < 1.0 else (1, m)


def fold(rows: list[dict], scale: int) -> list[dict]:
    """같은 종목을 묶어서 더합니다.

    **줄 수가 곧 종목 수가 아닙니다** — 자회사 조합마다 한 줄이라
    같은 회사가 여러 번 나옵니다. 주식과 원금(PRN), 콜과 풋은 서로 다른
    것이므로 묶는 열쇠에 함께 넣습니다."""
    agg: dict[tuple, dict] = {}
    for x in rows:
        key = (x["cusip"], x["class"], x["type"], x["putCall"])
        a = agg.get(key)
        if a is None:
            a = agg[key] = {"cusip": x["cusip"], "name": x["name"],
                            "class": x["class"], "value": 0, "shares": 0,
                            "lines": 0}
            if x["type"] != "SH":
                a["type"] = x["type"]
            if x["putCall"]:
                a["putCall"] = x["putCall"]
        a["value"] += x["value"] * scale
        a["shares"] += x["shares"]
        a["lines"] += 1
    out = sorted(agg.values(), key=lambda a: -a["value"])
    return out


def list_filings(contact: str) -> tuple[list[dict], list[dict]]:
    """13F-HR 을 전부 모읍니다 — 최근 목록 + 쪼개진 옛 목록까지.

    최근 목록(filings.recent)만 보면 2016년까지밖에 안 올라갑니다(실측:
    39건). 더 옛것은 filings.files 에 별도 파일로 쪼개져 있습니다."""
    body = get(f"https://data.sec.gov/submissions/CIK{CIK}.json", contact)
    if not body:
        return [], []
    sub = json.loads(body)
    fil = sub.get("filings") or {}
    blocks = [fil.get("recent") or {}]

    for f in (fil.get("files") or []):
        nm = f.get("name")
        if not nm:
            continue
        b = get(f"https://data.sec.gov/submissions/{nm}", contact)
        if not b:
            # 반쪽 목록으로 저장하면 옛 분기와 정정 표시가 사라집니다.
            # 다음 실행에서 다시 받도록 전체 목록을 실패로 돌립니다.
            return [], []
        blocks.append(json.loads(b))

    out, amend = [], []
    for block in blocks:
        for item in form_rows(block):
            form = item.pop("form")
            (out if form == FORM else amend).append(item)

    # 정정 공시(13F-HR/A)는 **일부러 안 받습니다.** 정정에는 통째로 다시 쓰는
    # 것과 빠진 것만 덧붙이는 것이 있는데, 둘을 반대로 처리하면 종목이 두 배가
    # 되거나 통째로 사라집니다. 실물을 한 번도 못 봤으므로 짐작해서 짜지 않고,
    # **있는지 없는지만 여기서 알립니다.** 나오면 그때 한 건을 열어 보고 넣습니다.
    amend = [x for x in amend if x["accession"] and x["period"]]
    out = [x for x in out if x["accession"] and x["period"]]
    out.sort(key=lambda x: x["period"])
    amend.sort(key=lambda x: x["period"])
    return out, amend


# 목차를 못 받은 것과, 목차는 받았는데 XML 이 아예 없는 것은 **다른 일**입니다.
NO_XML = "no-xml"


def filing_docs(acc: str, contact: str):
    """제출 폴더에서 **보유 목록 XML** 과 **표지** 를 함께 받습니다.

    이름을 짐작하지 않습니다. 목차가 주는 목록에서 primary_doc.xml 이 아닌
    .xml 중 가장 큰 것을 고릅니다 — 실측으로 이름이 분기마다 달랐습니다
    (56757.xml / form13fInfoTable.xml).

    XML 이 하나도 없으면 NO_XML 을 돌려줍니다. **고장이 아니라 옛 형식**입니다 —
    EDGAR 가 13F 에 XML 을 요구하기 전(2013년 중반 이전)에는 텍스트 문서였고,
    실측으로 1998-12-31 ~ 2013-03-31 의 58건이 전부 여기 해당합니다.
    이것을 '실패'로 세면 매주 58건이 찍혀서 **진짜 실패가 그 속에 묻힙니다.**"""
    a = re.sub(r"\D", "", acc)
    base = f"https://www.sec.gov/Archives/edgar/data/{int(CIK)}/{a}"
    body = get(f"{base}/index.json", contact)
    if not body:
        return None, None
    items = ((json.loads(body).get("directory") or {}).get("item") or [])
    best, cover, oversized = None, None, False
    for it in items:
        nm = (it.get("name") or "")
        low = nm.lower()
        if not low.endswith(".xml"):
            continue
        try:
            size = int(it.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if low == "primary_doc.xml":
            cover = nm
            continue
        if size > MAX_BYTES:
            oversized = True
            continue
        if best is None or size > best[1]:
            best = (nm, size)
    if not best:
        # 새 XML이 너무 큰 것은 옛 텍스트 형식과 다릅니다. 실패로 남겨야
        # 텔레그램이 울리고 한도가 부족하다는 사실을 알 수 있습니다.
        return (None, None) if oversized else (NO_XML, None)
    return get(f"{base}/{best[0]}", contact), (get(f"{base}/{cover}", contact)
                                               if cover else None)


def cover_totals(xml: bytes | None) -> tuple[int | None, int | None]:
    """표지가 스스로 밝힌 총액과 줄 수. 우리 계산을 맞춰 볼 잣대입니다."""
    if not xml:
        return None, None
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None, None
    tot = ent = None
    for el in root.iter():
        t = local(el.tag)
        if t == "tableValueTotal":
            tot = num(el.text)
        elif t == "tableEntryTotal":
            ent = num(el.text)
    return tot, ent


def configure(slug):
    """Select one registered investor without changing parser internals."""
    global CIK, OUT, MANAGER_NAME  # noqa: PLW0603
    investor = one(slug)
    CIK = investor.cik
    OUT = str(investor.output)
    MANAGER_NAME = investor.filing_name
    return investor


def main(slug=None) -> int:
    investor = configure(slug) if slug else None
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        print("받을 수 없습니다 — 비밀값 SEC_CONTACT 가 없습니다.")
        print("  SEC 는 이름 없는 요청을 거절합니다. 연락처 메일 주소를 밝혀야 합니다.")
        print("  저장소 Settings → Secrets and variables → Actions 에 넣어 주세요.")
        return 1

    # 이미 받아 둔 분기는 다시 받지 않습니다. 공시는 한 번 나오면 바뀌지
    # 않으므로, 분기마다 새 것 하나만 받으면 됩니다.
    old = {}
    prev = None
    # 지난번에 이미 알고 있던 정정 공시. 새로 뜬 것만 알리려고 들고 있습니다.
    known_amend: set[str] = set()
    had_prev = False
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                prev = json.load(f)
            saved_raw = str((prev.get("manager") or {}).get("cik") or "")
            saved_cik = saved_raw.zfill(10) if saved_raw else ""
            if saved_cik and saved_cik != CIK:
                print(f"옛 파일의 CIK {saved_cik}가 설정 {CIK}와 다릅니다. "
                      "서로 다른 투자자 자료를 합치지 않습니다.")
                return 1
            old = {q["accession"]: dict(q) for q in prev.get("quarters", [])}
            for q in prev.get("quarters", []):
                known_amend.update(q.get("amended_by") or [])
            had_prev = True
            print(f"이미 갖고 있는 분기 {len(old)}개 · "
                  f"이미 아는 정정 공시 {len(known_amend)}건")
        except Exception as e:                         # noqa: BLE001
            print(f"옛 파일을 읽지 못했습니다. 덮어쓰지 않습니다 — {e}")
            return 1

    filings, amends = list_filings(contact)
    if not filings:
        print("제출 목록을 받지 못했습니다. 아무것도 쓰지 않습니다.")
        return 1
    print(f"{FORM} {len(filings)}건 ({filings[0]['period']} ~ {filings[-1]['period']})")

    # 정정 공시가 난 분기는 **원본만으로는 불완전할 수 있습니다.** 아직 합치지
    # 않으므로, 어느 분기가 그런지 데이터에 표시해 두고 화면에서 밝힐 수 있게
    # 합니다. 조용히 넘어가면 그 분기만 소리 없이 틀립니다.
    amend_by = {}
    for x in amends:
        amend_by.setdefault(x["period"], []).append(x["accession"])
    print(f"정정 공시({FORM}/A) {len(amends)}건 · {len(amend_by)}개 분기")

    # 제출 목록에서 사라진 접수번호도 기존 기록에서는 보존합니다.
    # 목록은 탐색용이지, 이미 검산해 저장한 과거를 지우라는 명령이 아닙니다.
    saved = dict(old)
    got, failed, prexml = 0, 0, []
    for f in filings:
        keep = old.get(f["accession"])
        if keep:
            continue
        xml, cover = filing_docs(f["accession"], contact)
        if xml is NO_XML:
            # 고장이 아니라 옛 형식입니다. 따로 셉니다 — 실패로 세면
            # 매주 수십 건이 찍혀 진짜 실패가 묻힙니다.
            prexml.append(f["period"])
            continue
        if not xml:
            failed += 1
            continue
        try:
            rows = rows_of(xml)
        except ET.ParseError as e:
            print(f"    {f['period']} XML 을 읽지 못했습니다 — {e}")
            failed += 1
            continue
        if not rows:
            print(f"    {f['period']} 줄이 하나도 없습니다 — 건너뜁니다")
            failed += 1
            continue
        scale, ratio = unit_scale(rows)
        held = fold(rows, scale)
        total = sum(h["value"] for h in held)

        q = {"period": f["period"], "filed": f["filed"],
             "accession": f["accession"], "lines": len(rows),
             "unit": "thousands" if scale == 1000 else "usd",
             "total": total, "holdings": held}

        # 우리 합계를 **공시가 스스로 밝힌 총액**과 맞춰 봅니다. 이게 맞으면
        # 줄을 빠뜨리지도, 단위를 잘못 잡지도 않았다는 뜻입니다. 화면을 만들기
        # 전에 이 검산이 통과해야 합니다.
        ctot, cent = cover_totals(cover)
        mark = ""
        if ctot:
            want = ctot * scale
            off = abs(total - want) / want if want else 0
            if off > 0.005:
                q["total_mismatch"] = want
                mark = f"  ※ 공시 총액과 {off:.1%} 차이 (${want/1e9:,.1f}B)"
            else:
                mark = "  ✓"
        if cent and cent != len(rows):
            q["lines_mismatch"] = cent
            mark += f"  ※ 공시 줄 수 {cent} ≠ {len(rows)}"
        if f["period"] in amend_by:
            mark += "  ※ 정정 공시 있음"

        saved[f["accession"]] = q
        got += 1
        print(f"  {f['period']}  줄 {len(rows):>4} → 종목 {len(held):>3}  "
              f"금액÷주식수 {ratio:>8.2f} ({'천달러' if scale == 1000 else '달러'})  "
              f"합계 ${total/1e9:,.1f}B{mark}")

    if prexml:
        print(f"\nXML 이전 형식이라 건너뛴 분기 {len(prexml)}개 "
              f"({prexml[0]} ~ {prexml[-1]}) — 고장이 아닙니다.")
        print("  EDGAR 가 13F 에 XML 을 요구하기 전이라 텍스트 문서입니다.")
        print("  docs/masters-13f.md 의 'XML 이전' 항목을 보세요.")

    quarters = list(saved.values())
    if not quarters:
        print("받은 분기가 하나도 없습니다. 파일을 쓰지 않습니다.")
        return 1

    # 한 분기도 못 받았을 때 반쪽짜리 파일을 올리지 않는 장치입니다
    # (fetch_long.py 와 같은 생각 — CLAUDE.md 3번).
    if failed and not got:
        print(f"새로 받은 것이 없고 {failed}건 실패했습니다. 파일을 쓰지 않습니다.")
        return 1

    quarters.sort(key=lambda q: q["period"])

    # 정정 표시는 **이미 받아 둔 분기에도 매번 다시 붙입니다.** 예전에는 새로
    # 내려받는 분기에만 붙였는데, 공시는 한 번 받으면 다시 안 받으므로
    # **나중에 뜬 정정이 파일에 영영 안 적혔습니다.** 그래서 같은 정정을 매주
    # '새 것'으로 알리는 상태였습니다(시험에서 잡았습니다).
    # 목록에서 빠졌다는 이유로 이미 확인한 정정 접수번호는 지우지 않습니다.
    for q in quarters:
        got_a = amend_by.get(q["period"])
        if got_a:
            q["amended_by"] = list(dict.fromkeys([*(q.get("amended_by") or []), *got_a]))
    doc = {
        "updated": prev.get("updated") if prev else None,
        "source": "SEC Form 13F-HR (public domain)",
        "manager": {"cik": CIK, "name": MANAGER_NAME},
        "note": ("value in USD; rows folded by cusip. 13F shows US-listed long "
                 "positions only, filed 45 days after quarter end."),
        "quarters": quarters,
    }
    if doc != prev:
        doc["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        # 쓰는 도중 멈춰도 이전 JSON 은 완전한 상태로 남겨 둡니다.
        tmp = OUT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, OUT)
    else:
        print("공시 내용에 변화 없음 — 파일과 갱신 시각을 그대로 둡니다.")

    size = os.path.getsize(OUT)
    bad = [q for q in quarters if "total_mismatch" in q or "lines_mismatch" in q]
    amended = [q for q in quarters if "amended_by" in q]
    print(f"\n{OUT}  분기 {len(quarters)}개 · 새로 받은 것 {got}개 · "
          f"실패 {failed}개 · XML 이전 {len(prexml)}개 · {size:,} bytes")
    print(f"공시 총액과 어긋나는 분기: {len(bad)}개" +
          (f" — {', '.join(q['period'] for q in bad)}" if bad else " (전부 일치)"))
    if amended:
        print(f"정정 공시가 있는 분기 {len(amended)}개 (원본 숫자를 쓰는 중): "
              f"{', '.join(q['period'] for q in amended)}")
    # ── 새로 뜬 정정 공시를 알립니다 ────────────────────────────────
    # **정정은 자동으로 합치지 않습니다**(list_filings 의 주석 참고). 통째로
    # 다시 쓰는 것과 빠진 것만 덧붙이는 것이 있는데, 둘을 반대로 처리하면
    # 종목이 두 배가 되거나 통째로 사라집니다. 실물을 한 번도 못 봤으므로
    # **사람이 한 건을 열어 보게 알리는 것**이 지금 할 수 있는 최선입니다.
    #
    # 처음 받는 실행(옛 파일이 없음)에서는 알리지 않습니다 — 28년치가 통째로
    # '새 정정'으로 잡혀 알림이 의미를 잃습니다.
    fresh = [x for x in amends if x["accession"] not in known_amend]
    if fresh and had_prev:
        label = investor.name["ko"] if investor else "버크셔 해서웨이"
        lines = [f"{label} 13F 정정 공시(13F-HR/A) {len(fresh)}건이 새로 떴습니다.",
                 "",
                 "화면은 아직 원본 숫자를 쓰고 있습니다. 한 건을 열어 보고",
                 "통째로 다시 쓴 것인지 빠진 것만 덧붙인 것인지 확인해야 합니다.",
                 ""]
        for x in sorted(fresh, key=lambda v: v["period"]):
            acc = x["accession"]
            lines.append(f"  {x['period']}  냄 {x['filed']}  {acc}")
            lines.append(f"    https://www.sec.gov/Archives/edgar/data/"
                         f"{int(CIK)}/{acc.replace('-', '')}/")
        with open(ALERT, "a", encoding="utf-8") as f:
            if f.tell():
                f.write("\n")
            f.write("\n".join(lines) + "\n")
        print(f"\n*** 새 정정 공시 {len(fresh)}건 — {ALERT} 를 남겼습니다 ***")
        for ln in lines[5:]:
            print(ln)
    elif fresh:
        print(f"\n정정 공시 {len(fresh)}건이 있지만 첫 실행이라 알리지 않습니다.")
    else:
        print("\n새로 뜬 정정 공시 없음")

    last = quarters[-1]
    print(f"가장 최근 {last['period']}: 종목 {len(last['holdings'])}개 · "
          f"${last['total']/1e9:,.1f}B")
    for h in last["holdings"][:10]:
        print(f"    {h['name'][:34]:<34} ${h['value']/1e9:>7.2f}B  "
              f"{h['shares']:>14,}주  줄{h['lines']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--investor", default="berkshire")
    sys.exit(main(parser.parse_args().investor))
