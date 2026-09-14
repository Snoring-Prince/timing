"""
대가들의 선택 — 13F 공시를 받아 JSON 으로 (버크셔부터)

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
     버크셔는 자기 것과 자회사 14곳의 것을 함께 낸다. **자회사 조합마다
     한 줄**이라 같은 회사가 여러 번 나온다(2026-06-30 에 앨리가 세 줄).
     공시의 tableEntryTotal(89)은 **줄 수**이지 종목 수가 아니다.
     cusip 으로 묶어서 더해야 실제 보유가 나온다.

  3. 금액 단위가 도중에 바뀌었다
       2026-06-30  금액÷주식수 = 45.95     → 달러
       2016-12-31  금액÷주식수 = 0.0467    → 천 달러 (×1000 하면 46.69)
     날짜를 외워서 박지 않는다. **매 분기 금액÷주식수의 중앙값을 재서**
     1 보다 작으면 천 달러로 보고 1000을 곱한다. 종목 50개의 중앙값이라
     한두 종목이 이상해도 흔들리지 않는다.

저장: data/titans/berkshire.json  (금액은 전부 달러로 맞춰 둠)

주가는 아직 안 붙입니다. 13F 는 종목번호(CUSIP)만 주고 티커가 없어서,
먼저 연차보고서와 총액을 대조해 파이프라인이 맞는지 확인한 뒤에 갑니다.

저장 위치: scripts/fetch_13f.py
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from statistics import median

OUT = "data/titans/berkshire.json"

# 버크셔 해서웨이. 첫 번째인 이유는 docs/masters-13f.md 4번에 있습니다 —
# 연차보고서에 보유 종목이 나와 우리 계산을 대조할 수 있는 유일한 곳입니다.
CIK = "0001067983"
FORM = "13F-HR"

PAUSE = 0.25          # SEC 는 초당 10건을 넘지 말라고 합니다
MAX_BYTES = 8 * 1024 * 1024


def ua(contact: str) -> str:
    return f"itpaidoff.com 13F fetcher ({contact})"


def get(url: str, contact: str, tries: int = 3) -> bytes | None:
    """받아서 바이트로. 실패하면 None — 부르는 쪽이 판단합니다."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua(contact),
                "Accept": "application/json,application/xml,*/*",
                "Accept-Encoding": "identity",
            })
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except urllib.error.HTTPError as e:            # noqa: PERF203
            last = f"HTTP {e.code} {e.reason}"
            # 403 은 User-Agent 를 거절한 것이라 다시 걸어도 같습니다.
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1:
                break
            time.sleep(3.0 * (i + 1))
        except Exception as e:                         # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (i + 1))
        finally:
            time.sleep(PAUSE)
    print(f"    받지 못했습니다 — {last}\n      {url}")
    return None


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


def list_filings(contact: str) -> list[dict]:
    """13F-HR 을 전부 모읍니다 — 최근 목록 + 쪼개진 옛 목록까지.

    최근 목록(filings.recent)만 보면 2016년까지밖에 안 올라갑니다(실측:
    39건). 더 옛것은 filings.files 에 별도 파일로 쪼개져 있습니다."""
    body = get(f"https://data.sec.gov/submissions/CIK{CIK}.json", contact)
    if not body:
        return []
    sub = json.loads(body)
    fil = sub.get("filings") or {}
    blocks = [fil.get("recent") or {}]

    for f in (fil.get("files") or []):
        nm = f.get("name")
        if not nm:
            continue
        b = get(f"https://data.sec.gov/submissions/{nm}", contact)
        if b:
            blocks.append(json.loads(b))

    out = []
    for blk in blocks:
        forms = blk.get("form") or []
        for i, form in enumerate(forms):
            if form != FORM:
                continue
            g = lambda k: (blk.get(k) or [None] * len(forms))[i]   # noqa: E731
            out.append({"filed": g("filingDate"), "period": g("reportDate"),
                        "accession": g("accessionNumber")})
    out = [x for x in out if x["accession"] and x["period"]]
    out.sort(key=lambda x: x["period"])
    return out


def holdings_xml(acc: str, contact: str) -> bytes | None:
    """그 제출 폴더에서 **보유 목록 XML** 을 찾아 받습니다.

    이름을 짐작하지 않습니다. 목차가 주는 목록에서 primary_doc.xml 이
    아닌 .xml 을 고릅니다 — 실측으로 이름이 분기마다 달랐습니다."""
    a = re.sub(r"\D", "", acc)
    base = f"https://www.sec.gov/Archives/edgar/data/{int(CIK)}/{a}"
    body = get(f"{base}/index.json", contact)
    if not body:
        return None
    items = ((json.loads(body).get("directory") or {}).get("item") or [])
    best = None
    for it in items:
        nm = (it.get("name") or "")
        if not nm.lower().endswith(".xml") or nm.lower() == "primary_doc.xml":
            continue
        try:
            size = int(it.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if size > MAX_BYTES:
            continue
        # 후보가 여럿이면 큰 쪽이 정보표입니다(표지는 6KB 안쪽).
        if best is None or size > best[1]:
            best = (nm, size)
    if not best:
        print(f"    보유 목록 XML 을 목차에서 못 찾았습니다: {base}/index.json")
        return None
    return get(f"{base}/{best[0]}", contact)


def main() -> int:
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        print("받을 수 없습니다 — 비밀값 SEC_CONTACT 가 없습니다.")
        print("  SEC 는 이름 없는 요청을 거절합니다. 연락처 메일 주소를 밝혀야 합니다.")
        print("  저장소 Settings → Secrets and variables → Actions 에 넣어 주세요.")
        return 1

    # 이미 받아 둔 분기는 다시 받지 않습니다. 공시는 한 번 나오면 바뀌지
    # 않으므로, 분기마다 새 것 하나만 받으면 됩니다.
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                prev = json.load(f)
            old = {q["accession"]: q for q in prev.get("quarters", [])}
            print(f"이미 갖고 있는 분기 {len(old)}개")
        except Exception as e:                         # noqa: BLE001
            print(f"옛 파일을 읽지 못해 처음부터 받습니다 — {e}")

    filings = list_filings(contact)
    if not filings:
        print("제출 목록을 받지 못했습니다. 아무것도 쓰지 않습니다.")
        return 1
    print(f"{FORM} {len(filings)}건 ({filings[0]['period']} ~ {filings[-1]['period']})")

    quarters, got, failed = [], 0, 0
    for f in filings:
        keep = old.get(f["accession"])
        if keep:
            quarters.append(keep)
            continue
        xml = holdings_xml(f["accession"], contact)
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
        quarters.append({
            "period": f["period"], "filed": f["filed"],
            "accession": f["accession"],
            "lines": len(rows), "unit": "thousands" if scale == 1000 else "usd",
            "total": sum(h["value"] for h in held),
            "holdings": held,
        })
        got += 1
        print(f"  {f['period']}  줄 {len(rows):>4} → 종목 {len(held):>3}  "
              f"금액÷주식수 {ratio:>8.2f} ({'천달러' if scale == 1000 else '달러'})  "
              f"합계 ${sum(h['value'] for h in held)/1e9:,.1f}B")

    if not quarters:
        print("받은 분기가 하나도 없습니다. 파일을 쓰지 않습니다.")
        return 1

    # 한 분기도 못 받았을 때 반쪽짜리 파일을 올리지 않는 장치입니다
    # (fetch_long.py 와 같은 생각 — CLAUDE.md 3번).
    if failed and not got:
        print(f"새로 받은 것이 없고 {failed}건 실패했습니다. 파일을 쓰지 않습니다.")
        return 1

    quarters.sort(key=lambda q: q["period"])
    doc = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC Form 13F-HR (public domain)",
        "manager": {"cik": CIK, "name": "Berkshire Hathaway Inc"},
        "note": ("value in USD; rows folded by cusip. 13F shows US-listed long "
                 "positions only, filed 45 days after quarter end."),
        "quarters": quarters,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(OUT)
    print(f"\n{OUT}  분기 {len(quarters)}개 · 새로 받은 것 {got}개 · "
          f"실패 {failed}개 · {size:,} bytes")
    last = quarters[-1]
    print(f"가장 최근 {last['period']}: 종목 {len(last['holdings'])}개 · "
          f"${last['total']/1e9:,.1f}B")
    for h in last["holdings"][:10]:
        print(f"    {h['name'][:34]:<34} ${h['value']/1e9:>7.2f}B  "
              f"{h['shares']:>14,}주  줄{h['lines']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
