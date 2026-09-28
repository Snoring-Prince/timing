"""
대가들의 선택 — 새 투자자 후보 정찰(probe)

**이 스크립트는 파서가 아닙니다.** 후보마다 최근 13F 를 몇 분기 받아서 세고,
원본을 그대로 남길 뿐입니다. 누구를 넣을지·어떻게 보여 줄지는 이것을 읽은
뒤에 사람이 정합니다. `probe_sec.py` · `probe_annual.py` 와 같은 요령입니다.

무엇을 알아내려는 것인가
------------------------

2026-09-28 에 사용자와 여덟 명을 정했습니다(`CLAUDE.md` 9-3). 그중 버크셔는
이미 돌고 있고, 캐시 우드(ARK)는 **스스로 매일 공개**하므로 뒤로 미뤘습니다.
남은 여섯 곳을 넣기 전에 **짐작이 아니라 실측으로** 확인할 것이 있습니다.

    A  CIK 가 맞는가       — 받은 제출 목록의 회사 이름을 그대로 찍습니다
    B  아직 13F 를 내는가  — 가장 최근 분기와 제출일
    C  몇 종목인가         — 상위 50개만 보여 줄지 정하는 근거
    D  얼마나 자주 바뀌나  — 분기 사이에 새로 들어오고 빠지는 비율
    E  무엇으로 채워졌나   — 옵션·원금(PRN)·ETF 비중 (달리오는 ETF 가 많습니다)

**CIK 는 기억에서 온 값입니다.** 그래서 이름 검색도 같이 해서 둘을 나란히
찍습니다 — 틀리면 로그에서 바로 보입니다. 윌리엄 오닐처럼 13F 를 내는지
모르는 사람도 이름 검색만 해 봅니다.

비교 기준으로 버크셔를 같이 잽니다(종목이 적고 거의 안 바뀌는 곳).

왜 러너에서만 도는가
--------------------

개발 환경에서는 SEC 에 닿지 않습니다(프록시 403). 아티팩트도 못 받으므로
**핵심은 로그에도 찍습니다.**

비밀값
------

    저장소 Settings → Secrets and variables → Actions
      SEC_CONTACT   SEC 에 밝힐 연락처 메일 주소

**없으면 종료코드 1 로 끝냅니다.** 결과 파일에는 연락처를 적지 않습니다.
**하나도 못 받았을 때만 실패입니다** — "그 회사는 13F 가 없더라"도 답입니다.

저장 위치: scripts/probe_titans.py
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from urllib.parse import quote

import fetch_13f as f13
from titans.sec import get

OUT_DIR = "titans-probe"

# 후보 — 사용자와 정한 여섯 곳 + 비교 기준 버크셔.
# `cik` 는 기억에서 온 값이라 틀릴 수 있습니다. `search` 로 이름 검색을 같이 합니다.
# 아팔루사는 운용 법인이 2016년에 바뀌어 옛 CIK 도 같이 봅니다.
CANDIDATES = [
    {"slug": "berkshire",   "who": "Warren Buffett",       "style": "value",
     "ciks": ["0001067983"], "search": "Berkshire Hathaway"},
    {"slug": "himalaya",    "who": "Li Lu",                "style": "value",
     "ciks": ["0001709323"], "search": "Himalaya Capital"},
    {"slug": "gotham",      "who": "Joel Greenblatt",      "style": "formula",
     "ciks": ["0001510387"], "search": "Gotham Asset Management"},
    {"slug": "bridgewater", "who": "Ray Dalio",            "style": "macro",
     "ciks": ["0001350694"], "search": "Bridgewater Associates"},
    {"slug": "duquesne",    "who": "Stanley Druckenmiller", "style": "macro",
     "ciks": ["0001536411"], "search": "Duquesne Family Office"},
    {"slug": "pershing",    "who": "Bill Ackman",          "style": "activist",
     "ciks": ["0001336528"], "search": "Pershing Square Capital"},
    {"slug": "appaloosa",   "who": "David Tepper",         "style": "contrarian",
     "ciks": ["0001656456", "0001006438"], "search": "Appaloosa"},
]
# 13F 를 내는지조차 모르는 이름 — 검색만 합니다.
SEARCH_ONLY = [
    {"who": "William O'Neil", "search": "O'Neil"},
    {"who": "William O'Neil", "search": "ONeil"},
]

# 이름으로 ETF 를 어림합니다. **정의가 아니라 어림입니다** — 로그에도 그렇게 적습니다.
ETF_HINT = re.compile(r"\bETF\b|ISHARES|SPDR|VANGUARD|INVESCO QQQ|SELECT SECTOR|"
                      r"\bINDEX\b|\bTR(UST)?\b.*\bUNIT", re.I)


def save(path, data):
    full = os.path.join(OUT_DIR, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(full, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
        f.write(data)


def search_names(term, contact):
    """EDGAR 회사 검색(13F-HR 을 낸 곳). 받은 것을 저장하고 CIK·이름만 어림으로 뽑습니다."""
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
           f"&company={quote(term)}&type=13F-HR&dateb=&owner=include&count=40&output=atom")
    body = get(url, contact)
    if not body:
        return None
    text = body.decode("utf-8", "replace")
    save(f"search/{re.sub(r'[^A-Za-z0-9]+', '_', term)}.xml", body)
    hits = []
    # 회사가 여럿이면 목록, 하나면 그 회사의 공시 목록이 옵니다. 둘 다 훑습니다.
    for m in re.finditer(r"<cik>(\d+)</cik>.*?<name>([^<]+)</name>", text, re.S):
        hits.append((m.group(1).zfill(10), m.group(2).strip()))
    for m in re.finditer(r"<name>([^<]+)</name>.*?<cik>(\d+)</cik>", text, re.S):
        hits.append((m.group(2).zfill(10), m.group(1).strip()))
    for m in re.finditer(r"CIK=(\d{10})[^>]*>\s*([^<]{2,80})<", text):
        hits.append((m.group(1), m.group(2).strip()))
    seen, out = set(), []
    for cik, name in hits:
        if cik not in seen:
            seen.add(cik)
            out.append((cik, name))
    return {"bytes": len(body), "hits": out[:15], "head": "" if out else text[:600]}


def issuer_rows(held):
    """주식(SH)·옵션 아님만 발행사(CUSIP 앞 6자리)로 묶습니다 — 화면과 같은 범위."""
    agg = {}
    for h in held:
        if h.get("putCall") or h.get("type", "SH") != "SH":
            continue
        k = h["cusip"][:6]
        a = agg.setdefault(k, {"key": k, "name": h["name"], "value": 0, "shares": 0})
        a["value"] += h["value"]
        a["shares"] += h["shares"]
    return sorted(agg.values(), key=lambda a: -a["value"])


def measure(held, total):
    sh = issuer_rows(held)
    stock_total = sum(a["value"] for a in sh) or 1
    opt = [h for h in held if h.get("putCall")]
    prn = [h for h in held if h.get("type", "SH") == "PRN"]
    etf = sum(a["value"] for a in sh if ETF_HINT.search(a["name"]))
    cum, n80 = 0, 0
    for a in sh:
        cum += a["value"]
        n80 += 1
        if cum >= 0.8 * stock_total:
            break
    return {
        "positions_all": len(held),
        "issuers_sh": len(sh),
        "total_all": total,
        "total_sh": stock_total,
        "options": {"count": len(opt), "value": sum(h["value"] for h in opt)},
        "prn": {"count": len(prn), "value": sum(h["value"] for h in prn)},
        "etf_name_share": etf / stock_total,
        "top10_share": sum(a["value"] for a in sh[:10]) / stock_total,
        "top50_share": sum(a["value"] for a in sh[:50]) / stock_total,
        "issuers_for_80pct": n80,
        "top10": [(a["name"], round(a["value"] / stock_total, 4)) for a in sh[:10]],
        "_issuers": {a["key"]: a for a in sh},
    }


def turnover(prev, cur):
    """두 분기 사이에 발행사 기준으로 무엇이 들어오고 나갔나."""
    p, c = prev["_issuers"], cur["_issuers"]
    new = [k for k in c if k not in p]
    gone = [k for k in p if k not in c]
    same = [k for k in c if k in p]
    moved = [k for k in same if p[k]["shares"] and
             abs(c[k]["shares"] / p[k]["shares"] - 1) > 0.05]
    ct, pt = cur["total_sh"], prev["total_sh"]
    return {
        "new_count": len(new), "new_value_share": sum(c[k]["value"] for k in new) / ct,
        "gone_count": len(gone), "gone_value_share": sum(p[k]["value"] for k in gone) / pt,
        "moved_over_5pct": len(moved), "held": len(same),
    }


def pct(x):
    return f"{x*100:5.1f}%"


def probe_one(cand, contact, depth):
    print(f"\n━━ {cand['who']}  ({cand['slug']}) ━━")
    report = {"who": cand["who"], "slug": cand["slug"], "style": cand["style"], "ciks": []}
    found = search_names(cand["search"], contact)
    if found:
        print(f"  이름 검색 '{cand['search']}' → {len(found['hits'])}곳")
        for cik, name in found["hits"][:8]:
            print(f"      {cik}  {name}")
        if not found["hits"]:
            print("      (검색 결과를 못 읽었습니다 — 원본 앞부분)")
            print("      " + found["head"][:300].replace("\n", " "))
    report["search"] = found

    for cik in cand["ciks"]:
        f13.CIK = cik
        body = get(f"https://data.sec.gov/submissions/CIK{cik}.json", contact)
        if not body:
            print(f"  CIK {cik}: 제출 목록을 받지 못했습니다")
            report["ciks"].append({"cik": cik, "error": "no submissions"})
            continue
        sub = json.loads(body)
        name = sub.get("name", "?")
        filings, amends = f13.list_filings(contact)
        r = {"cik": cik, "name": name, "filings": len(filings), "amendments": len(amends)}
        print(f"  CIK {cik}: {name}")
        if not filings:
            print("      13F-HR 없음")
            report["ciks"].append(r)
            continue
        last = filings[-1]
        age = (date.today() - date.fromisoformat(last["period"])).days
        r.update(first=filings[0]["period"], last=last["period"], last_filed=last["filed"],
                 days_since_last_period=age)
        stale = "  ← 오래됨: 더 이상 내지 않을 수 있습니다" if age > 200 else ""
        print(f"      13F-HR {len(filings)}건 · {filings[0]['period']} ~ {last['period']}"
              f" (제출 {last['filed']}) · 정정 {len(amends)}건{stale}")

        quarters = []
        for f in reversed(filings):
            if len(quarters) >= depth:
                break
            xml, cover = f13.filing_docs(f["accession"], contact)
            if xml is f13.NO_XML or not xml:
                print(f"      {f['period']} XML 없음/받기 실패 — 멈춥니다")
                break
            try:
                rows = f13.rows_of(xml)
                scale, _ = f13.unit_scale(rows, f["filed"])
            except (ET.ParseError, TypeError, ValueError) as e:
                print(f"      {f['period']} 읽기 실패 — {e}")
                break
            held = f13.fold(rows, scale)
            total = sum(h["value"] for h in held)
            ctot, _ = f13.cover_totals(cover)
            m = measure(held, total)
            m.update(period=f["period"], filed=f["filed"], lines=len(rows), bytes=len(xml),
                     cover_total=(ctot * scale if ctot else None))
            quarters.append(m)
            if len(quarters) <= 2:
                save(f"{cand['slug']}/{cik}/{f['period']}-infotable.xml", xml)

        if not quarters:
            report["ciks"].append(r)
            continue
        quarters.reverse()                      # 옛 분기 → 최근 분기
        cur = quarters[-1]
        print(f"      최근 {cur['period']}: 줄 {cur['lines']:,} · 묶은 종목 {cur['positions_all']:,}"
              f" · 주식 발행사 {cur['issuers_sh']:,} · 원문 {cur['bytes']/1e6:.1f}MB")
        print(f"      총액 ${cur['total_all']/1e9:,.1f}B (주식 ${cur['total_sh']/1e9:,.1f}B)"
              + (f" · 표지 총액 ${cur['cover_total']/1e9:,.1f}B" if cur["cover_total"] else ""))
        print(f"      옵션 {cur['options']['count']}줄 ${cur['options']['value']/1e9:,.1f}B"
              f" · 원금(PRN) {cur['prn']['count']}줄 ${cur['prn']['value']/1e9:,.1f}B"
              f" · 이름으로 어림한 ETF {pct(cur['etf_name_share'])}")
        print(f"      상위 10 {pct(cur['top10_share'])} · 상위 50 {pct(cur['top50_share'])}"
              f" · 80% 까지 {cur['issuers_for_80pct']}종목")
        for nm, w in cur["top10"]:
            print(f"        {pct(w)}  {nm}")

        turns = [turnover(a, b) for a, b in zip(quarters, quarters[1:])]
        if turns:
            print(f"      분기 사이 변화 (최근 {len(turns)}번, 발행사 기준):")
            for q, t in zip(quarters[1:], turns):
                print(f"        {q['period']}  새로 {t['new_count']:4d} ({pct(t['new_value_share'])})"
                      f"  빠짐 {t['gone_count']:4d} ({pct(t['gone_value_share'])})"
                      f"  계속 {t['held']:4d} 중 5%넘게 바뀜 {t['moved_over_5pct']:4d}")
        # 최근 상위 10이 창 안에서 몇 분기 연속 있었나
        streaks = []
        for key in list(cur["_issuers"])[:10]:
            n = 0
            for q in reversed(quarters):
                if key in q["_issuers"]:
                    n += 1
                else:
                    break
            streaks.append(n)
        print(f"      최근 상위 10의 연속 보유(최대 {len(quarters)}분기): {streaks}")

        for q in quarters:
            q.pop("_issuers", None)
        r.update(quarters=quarters, turnover=turns, top10_streaks=streaks)
        report["ciks"].append(r)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=8, help="후보마다 최근 몇 분기")
    ap.add_argument("--only", default="", help="쉼표로 slug 몇 개만")
    args = ap.parse_args()

    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        print("받을 수 없습니다 — 비밀값 SEC_CONTACT 가 없습니다.")
        print("  저장소 Settings → Secrets and variables → Actions 에 넣어 주세요.")
        return 1

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    cands = [c for c in CANDIDATES if not only or c["slug"] in only]
    print(f"정찰 {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · 후보 {len(cands)}곳 · "
          f"최근 {args.depth}분기")

    reports, got = [], 0
    for c in cands:
        rep = probe_one(c, contact, args.depth)
        got += sum(1 for x in rep["ciks"] if x.get("quarters"))
        reports.append(rep)

    print("\n━━ 이름만 검색 ━━")
    extra = []
    for s in SEARCH_ONLY:
        found = search_names(s["search"], contact)
        print(f"  {s['who']} · '{s['search']}' → "
              + ("받지 못함" if not found else f"{len(found['hits'])}곳"))
        for cik, name in (found or {}).get("hits", [])[:10]:
            print(f"      {cik}  {name}")
        extra.append({**s, "result": found})

    print("\n━━ 한눈에 ━━")
    print(f"  {'후보':<22}{'최근 분기':<12}{'발행사':>7}{'상위50':>8}{'새로(중앙)':>11}{'ETF어림':>9}")
    for rep in reports:
        for x in rep["ciks"]:
            qs = x.get("quarters") or []
            if not qs:
                continue
            cur = qs[-1]
            news = sorted(t["new_count"] / max(1, qs[i + 1]["issuers_sh"])
                          for i, t in enumerate(x["turnover"]))
            mid = news[len(news) // 2] if news else 0
            print(f"  {rep['who'][:21]:<22}{cur['period']:<12}{cur['issuers_sh']:>7,}"
                  f"{pct(cur['top50_share']):>8}{pct(mid):>11}{pct(cur['etf_name_share']):>9}")
    print("  (새로 = 분기마다 새로 들어온 발행사 비율의 중앙값 · ETF 는 이름으로 어림한 값)")

    save("summary.json", json.dumps({"generated": datetime.now(timezone.utc).isoformat(),
                                     "candidates": reports, "search_only": extra},
                                    ensure_ascii=False, indent=1))
    if not got:
        print("\n하나도 받지 못했습니다 — 실패로 끝냅니다.")
        return 1
    print(f"\n받은 곳 {got} · 결과는 {OUT_DIR}/ 에 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
