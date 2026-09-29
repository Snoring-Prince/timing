"""
대가들의 선택 — 새 투자자 후보 정찰(probe)

**이 스크립트는 파서가 아닙니다.** 후보마다 최근 13F 를 몇 분기 받아서 세고,
원본을 그대로 남길 뿐입니다. 누구를 넣을지·어떻게 보여 줄지는 이것을 읽은
뒤에 사람이 정합니다. `probe_sec.py` · `probe_annual.py` 와 같은 요령입니다.

무엇을 알아내려는 것인가
------------------------

2026-09-28 에 사용자와 여덟 명을 정했습니다(`CLAUDE.md` 9-3). 그중 버크셔는
이미 돌고 있고, 캐시 우드(ARK)는 **스스로 매일 공개**하므로 뒤로 미뤘습니다.
(2026-09-29: 일곱 명을 다 넣은 뒤 ARK 도 13F 로 넣기로 해 후보에 더했습니다 —
벤치마크 stockcircle 도 캐시 우드를 분기 단위, 곧 13F 로 보여 줍니다.)
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
# 테퍼는 두 CIK 를 이어 붙이기로 했습니다(2026-09-28) — 옛 번호는 2015년에 멈췄으니 한 번만 받으면 됩니다.
# `cik` 는 기억에서 온 값이라 틀릴 수 있습니다. `search` 로 이름 검색을 같이 합니다.
# 아팔루사는 운용 법인이 2016년에 바뀌어 옛 CIK 도 같이 봅니다.
CANDIDATES = [
    {"slug": "berkshire",   "who": "Warren Buffett",       "style": "value",
     "ciks": ["0001067983"], "search": "Berkshire Hathaway"},
    {"slug": "himalaya",    "who": "Li Lu",                "style": "value",
     "ciks": ["0001709323"], "search": "Himalaya Capital"},
    # 그린블라트(고담)는 1차 정찰(2026-09-28)에서 1,571종목 · 상위 50이 41% ·
    # 1위가 S&P 500 ETF 라 뺐습니다(사용자 판단). 대신 클라만입니다.
    {"slug": "baupost",     "who": "Seth Klarman",         "style": "value",
     "ciks": ["0001061768"], "search": "Baupost"},
    # 달리오(브리지워터)는 2차 정찰 뒤 뺐습니다(사용자 판단, 2026-09-28) — 992종목 ·
    # 상위 50이 62% · ETF 가 약 30%. 대신 하워드 막스(오크트리)를 잽니다.
    # 오크트리의 본업은 채권·부실채권이라 13F 에는 주식 쪽만 나옵니다 — 얼마나
    # 보이는지가 이번 정찰의 질문입니다.
    {"slug": "oaktree",     "who": "Howard Marks",         "style": "distressed",
     "ciks": ["0000949509"], "search": "Oaktree Capital"},
    {"slug": "duquesne",    "who": "Stanley Druckenmiller", "style": "macro",
     "ciks": ["0001536411"], "search": "Duquesne Family Office"},
    # 애크먼: 2026 2분기는 옛 번호가 13F 대신 13F-NT 를 냈고, 대신 낸 곳이
    # PERSHING SQUARE INC.(CIK 0002026053 · 028-25746)였다(정찰 4차). 그 번호의
    # 13F 가 퍼싱의 보유만 담는지, 옛 번호의 마지막 13F 와 이어지는지를 잰다(정찰 5차).
    {"slug": "pershing",    "who": "Bill Ackman",          "style": "activist",
     "ciks": ["0002026053", "0001336528"], "search": "Pershing Square",
     "predecessor": "0001336528"},
    {"slug": "appaloosa",   "who": "David Tepper",         "style": "contrarian",
     "ciks": ["0001656456", "0001006438"], "search": "Appaloosa",
     # 옛 번호(1999~2015)를 새 번호(2016~)에 이어 붙이기 전에, 같은 포트폴리오가
     # 이어진 것인지(= 회사가 바뀐 게 아니라 껍데기만 바뀐 것인지) 잰다.
     "predecessor": "0001006438"},
    # 캐시 우드(ARK) — 마지막 여덟째. ETF 를 굴리는 운용사라 종목이 많고 자주 바뀔 수 있어,
    # 종목 수·상위 50 비중·분기마다 새로 드는 비율을 먼저 잰다. CIK 는 기억에서 온 값.
    {"slug": "ark",         "who": "Cathie Wood",          "style": "growth",
     "ciks": ["0001697748"], "search": "ARK Investment"},
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
    """EDGAR 회사 검색(13F-HR 을 낸 곳). 받은 것을 저장하고 CIK 를 모아 제출 목록의 이름을 붙입니다."""
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
           f"&company={quote(term)}&type=13F-HR&dateb=&owner=include&count=40&output=atom")
    body = get(url, contact)
    if not body:
        return None
    text = body.decode("utf-8", "replace")
    save(f"search/{re.sub(r'[^A-Za-z0-9]+', '_', term)}.xml", body)
    # 회사가 여럿이면 목록, 하나면 그 회사의 공시 목록이 옵니다. **번호만** 모읍니다 —
    # 이름은 아래에서 제출 목록으로 받습니다.
    ciks = [c.zfill(10) for c in re.findall(r"<cik>(\d+)</cik>", text)]
    ciks += re.findall(r"CIK=(\d{10})", text)
    out = list(dict.fromkeys(ciks))
    # 1차 실행에서 이름 칸에 'Webmaster'(피드 작성자)가 찍혔습니다. atom 의 모양을
    # 짐작해 고치지 않고, 이미 읽을 줄 아는 제출 목록에서 **진짜 이름**을 받습니다.
    named = []
    for cik in out[:8]:
        raw = get(f"https://data.sec.gov/submissions/CIK{cik}.json", contact)
        try:
            named.append((cik, json.loads(raw)["name"] if raw else "(이름 못 받음)"))
        except (ValueError, KeyError):
            named.append((cik, "(이름 못 읽음)"))
    return {"bytes": len(body), "hits": named, "head": "" if out else text[:600]}


def notice_managers(cik, acc, contact):
    """13F-NT 표지에서 '대신 신고한 운용사'의 이름·파일번호·CIK 를 찍습니다."""
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/primary_doc.xml"
    body = get(url, contact)
    if not body:
        print(f"      13F-NT {acc}: 표지를 받지 못했습니다")
        return
    save(f"notice/{cik}-{acc}.xml", body)
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"      13F-NT {acc}: 표지를 읽지 못했습니다 — {e}")
        return
    found = 0
    for el in root.iter():
        # 바깥 묶음(otherManagersInfo)과 안쪽 한 칸(otherManager)이 둘 다 걸리므로
        # 자식이 전부 잎인 **안쪽 칸**만 찍습니다.
        if "othermanager" not in f13.local(el.tag).lower() or not len(el) or any(len(x) for x in el):
            continue
        leaves = {f13.local(x.tag): x.text.strip() for x in el.iter()
                  if x is not el and len(x) == 0 and (x.text or "").strip()}
        if leaves:
            found += 1
            print(f"      13F-NT {acc} 대신 신고: " + " · ".join(f"{k} {v}" for k, v in leaves.items()))
    if not found:
        print(f"      13F-NT {acc}: 대신 신고한 운용사 항목을 못 찾았습니다 (원본 저장함)")


def who_signed(cover):
    """표지의 운용사 이름·주소·서명자. 두 번호가 같은 사람들인지 보는 재료."""
    if not cover:
        return {}
    try:
        root = ET.fromstring(cover)
    except ET.ParseError:
        return {}
    out = {}
    def first(path):
        for el in root.iter():
            if f13.local(el.tag) != path[0]:
                continue
            for sub in el.iter():
                if f13.local(sub.tag) == path[1] and (sub.text or "").strip():
                    return sub.text.strip()
        return ""
    out["manager"] = first(("filingManager", "name"))
    out["city"] = ", ".join(x for x in (first(("filingManager", "city")),
                                         first(("filingManager", "stateOrCountry"))) if x)
    out["signer"] = " · ".join(x for x in (first(("signatureBlock", "name")),
                                            first(("signatureBlock", "title"))) if x)
    return out


def report_scope(cover, xml, period):
    """이 13F 가 **누구의 보유**를 담았는가 — 표지의 보고 종류와 함께 실린 운용사,
    그리고 표의 줄마다 붙는 '다른 운용사' 번호를 센다(애크먼 대신 신고자 정찰).

    `13F HOLDINGS REPORT` 면 이 운용사 것만, `13F COMBINATION REPORT` 면 다른
    운용사 몫이 섞여 있다. 섞였으면 줄마다 `otherManager` 번호로 누구 몫인지 갈린다."""
    kind, included = "?", []
    try:
        root = ET.fromstring(cover) if cover else None
    except ET.ParseError:
        root = None
    if root is not None:
        for el in root.iter():
            tag = f13.local(el.tag)
            if tag == "reportType" and (el.text or "").strip():
                kind = el.text.strip()
            # 함께 실린 운용사 한 칸 — 자식이 전부 잎인 안쪽 칸만(13F-NT 와 같은 요령).
            if "othermanager" in tag.lower() and len(el) and not any(len(x) for x in el):
                leaves = {f13.local(x.tag): x.text.strip() for x in el.iter()
                          if x is not el and len(x) == 0 and (x.text or "").strip()}
                if leaves:
                    included.append(" · ".join(f"{k} {v}" for k, v in leaves.items()))
    tags = re.findall(rb"<(?:\w+:)?otherManager>\s*([^<]*?)\s*</", xml or b"")
    rows = len(re.findall(rb"<(?:\w+:)?infoTable>", xml or b""))
    by = {}
    for t in tags:
        by[t.decode("utf-8", "replace")] = by.get(t.decode("utf-8", "replace"), 0) + 1
    print(f"      {period} 표지: 보고 종류 {kind} · 함께 실린 운용사 {len(included)}곳")
    for x in included:
        print(f"        {x}")
    print(f"      {period} 표: {rows}줄 중 다른 운용사 번호가 붙은 줄 {sum(by.values())}"
          + (" (" + ", ".join(f"{k or '빈칸'}: {v}" for k, v in sorted(by.items())) + ")" if by else ""))


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
    # 금액 ÷ 주식수 중앙값 = 대략 주가. 1달러 아래로 나오면 금액이 '천 달러'
    # 단위일 가능성이 큽니다(드러켄밀러 총액이 $0.0B 로 나온 까닭을 가리는 한 줄).
    per = sorted(h["value"] / h["shares"] for h in held
                 if h.get("shares") and not h.get("putCall") and h.get("type", "SH") == "SH")
    return {
        "implied_price_median": per[len(per) // 2] if per else None,
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
        biz = (sub.get("addresses") or {}).get("business") or {}
        former = [x.get("name", "") for x in sub.get("formerNames") or []]
        print(f"      등록 주소 {biz.get('city') or '?'}, {biz.get('stateOrCountry') or '?'}"
              f" · 설립지 {sub.get('stateOfIncorporation') or '?'}"
              + (f" · 옛 이름 {', '.join(former)}" if former else ""))
        r["_filings"] = filings
        # 13F 계열 제출을 날짜순으로 최근 몇 건 — '공시가 안 보인다'가 늦은 것인지,
        # 13F-NT(다른 곳이 대신 냄) 같은 다른 서식인지 가린다(애크먼 2분기).
        rec = (sub.get("filings") or {}).get("recent") or {}
        recent13 = [(fm, fd, rd) for fm, fd, rd in zip(rec.get("form", []), rec.get("filingDate", []),
                                                       rec.get("reportDate", [])) if fm.startswith("13F")]
        print("      최근 13F 계열 제출: " + (" · ".join(f"{fm} {rd or '?'}→{fd}"
                                                 for fm, fd, rd in recent13[:5]) or "없음"))
        # 13F-NT 는 "내 보유는 다른 운용사가 대신 신고했다"는 알림입니다(애크먼
        # 2026 2분기). 누가 대신 냈는지는 그 알림의 표지에 적혀 있으니 읽습니다.
        for fm, acc in zip(rec.get("form", []), rec.get("accessionNumber", [])):
            if fm == "13F-NT":
                notice_managers(cik, acc, contact)
                break
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
            if not quarters:
                report_scope(cover, xml, f["period"])
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
        if cur.get("implied_price_median") is not None:
            print(f"      금액÷주식수 중앙값 ${cur['implied_price_median']:,.2f}"
                  + ("  ← 1달러 아래: 금액이 천 달러 단위일 수 있습니다" if cur["implied_price_median"] < 1 else ""))
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
    if cand.get("predecessor"):
        continuity(cand, report, contact)
    for x in report["ciks"]:
        x.pop("_filings", None)             # summary.json 에는 목록 전체를 싣지 않는다
    return report


def continuity(cand, report, contact):
    """옛 번호의 **마지막** 분기와 새 번호의 **첫** 분기를 나란히 놓는다.

    회사가 바뀐 것이면 보유 종목이 딴판이고, 껍데기(법인·주소)만 바뀐 것이면
    같은 종목이 같은 무게로 이어진다. 숫자로 가린다."""
    old = next((x for x in report["ciks"] if x["cik"] == cand["predecessor"]), None)
    new = next((x for x in report["ciks"] if x["cik"] != cand["predecessor"]), None)
    if not old or not new or not old.get("_filings") or not new.get("_filings"):
        print("  이어짐 확인: 두 번호의 목록을 다 받지 못했습니다")
        return
    # 새 번호의 '처음'은 옛 번호가 멈춘 **뒤의** 첫 분기다. 새 번호가 그 전부터 다른
    # 것을 내고 있었을 수 있다(애크먼: 지주회사가 2025년부터 하워드 휴즈 한 종목만 냄).
    # 그냥 첫 공시를 잡았더니 −274일 짜리 엉뚱한 비교가 나왔다(정찰 5차).
    last_old = old["_filings"][-1]
    after = [f for f in new["_filings"] if f["period"] > last_old["period"]]
    if not after:
        print("  이어짐 확인: 옛 번호가 멈춘 뒤의 새 공시가 없습니다")
        return
    sides = []
    for side, f in (("옛 마지막", last_old), ("새 처음", after[0])):
        f13.CIK = old["cik"] if side == "옛 마지막" else new["cik"]
        xml, cover = f13.filing_docs(f["accession"], contact)
        if xml is f13.NO_XML or not xml:
            print(f"  이어짐 확인: {side} {f['period']} 원문을 받지 못했습니다")
            return
        rows = f13.rows_of(xml)
        scale, _ = f13.unit_scale(rows, f["filed"])
        m = measure(f13.fold(rows, scale), 0)
        sides.append((side, f, m, who_signed(cover)))
        save(f"{cand['slug']}/continuity-{f13.CIK}-{f['period']}-infotable.xml", xml)
    (_, fo, mo, wo), (_, fn, mn, wn) = sides
    a, b = mo["_issuers"], mn["_issuers"]
    both = set(a) & set(b)
    kept_old = sum(a[k]["value"] for k in both) / max(1, sum(x["value"] for x in a.values()))
    kept_new = sum(b[k]["value"] for k in both) / max(1, sum(x["value"] for x in b.values()))
    print(f"\n  ── 이어짐 확인: {cand['who']} ──")
    for side, f, m, w in sides:
        print(f"    {side:<6} {f['period']} (제출 {f['filed']}) · 발행사 {m['issuers_sh']}"
              f" · 운용사 {w.get('manager') or '?'} · {w.get('city') or '?'}"
              f" · 서명 {w.get('signer') or '?'}")
    print(f"    두 분기에 다 있는 발행사 {len(both)}곳")
    print(f"    옛 마지막 금액 중 새 처음에도 있는 몫 {pct(kept_old)}"
          f" · 새 처음 금액 중 옛 마지막에도 있던 몫 {pct(kept_new)}")
    gap = (date.fromisoformat(fn["period"]) - date.fromisoformat(fo["period"])).days
    print(f"    두 분기 사이 {gap}일" + ("  (바로 다음 분기)" if 0 < gap <= 92 else "  ← 빈 분기가 있습니다"))
    report["continuity"] = {"old": fo["period"], "new": fn["period"], "gap_days": gap,
                            "shared_issuers": len(both), "kept_old": kept_old,
                            "kept_new": kept_new, "old_cover": wo, "new_cover": wn}
    overlap(cand, old, new, after[0], contact, report)


def holdings_of(cik, filing, contact):
    """한 공시의 주식(옵션 아님)을 CUSIP 9자리별 {이름, 주식수, 금액} 으로."""
    f13.CIK = cik
    xml, _ = f13.filing_docs(filing["accession"], contact)
    if xml is f13.NO_XML or not xml:
        return None
    rows = f13.rows_of(xml)
    scale, _ = f13.unit_scale(rows, filing["filed"])
    out = {}
    for h in f13.fold(rows, scale):
        if h.get("putCall") or h.get("type", "SH") != "SH":
            continue
        a = out.setdefault(h["cusip"], {"name": h["name"], "shares": 0, "value": 0})
        a["shares"] += h["shares"]
        a["value"] += h["value"]
    return out


def overlap(cand, old, new, first_after, contact, report):
    """두 번호가 **같은 분기**를 둘 다 낸 경우 — 합칠지, 겹치는 것을 한 번만 셀지 가린다.

    애크먼: 옛 번호(펀드들)와 새 번호(지주회사)가 2025-06-30 ~ 2026-03-31 에 각자 냈고,
    2026-06-30 부터는 새 번호가 둘을 합쳐 낸다. 두 공시에 같이 나오는 종목의 주식 수를
    나란히 찍고, 합쳐 낸 첫 분기의 주식 수와 견준다 —
      합계 ≈ 다음 분기  → 서로 다른 주머니(더한다)
      한쪽 ≈ 다음 분기  → 같은 주식을 두 번 신고(한 번만 센다)"""
    olds = {f["period"]: f for f in old["_filings"]}
    shared_periods = [f for f in new["_filings"] if f["period"] in olds]
    if not shared_periods:
        return
    print(f"\n  ── 같은 분기를 두 번호가 다 냄: {len(shared_periods)}분기 ──")
    rows_out, keys = [], set()
    for fn in shared_periods:
        a = holdings_of(old["cik"], olds[fn["period"]], contact)
        b = holdings_of(new["cik"], fn, contact)
        if a is None or b is None:
            print(f"    {fn['period']}: 원문을 받지 못했습니다")
            continue
        both = sorted(set(a) & set(b))
        keys |= set(both)
        print(f"    {fn['period']}  옛 {len(a)}종목 ${sum(x['value'] for x in a.values())/1e9:,.2f}B"
              f" · 새 {len(b)}종목 ${sum(x['value'] for x in b.values())/1e9:,.2f}B · 둘 다 {len(both)}")
        for c in both:
            print(f"      {c} {a[c]['name'][:28]:<28} 옛 {a[c]['shares']:>14,}주"
                  f" · 새 {b[c]['shares']:>14,}주 · 합 {a[c]['shares']+b[c]['shares']:>14,}주")
        only_b = sorted(set(b) - set(a))
        if only_b:
            print("      새 번호에만: " + ", ".join(f"{b[c]['name'][:24]} {b[c]['shares']:,}주" for c in only_b))
        rows_out.append({"period": fn["period"], "both": {c: [a[c]["shares"], b[c]["shares"]] for c in both},
                         "only_new": {c: b[c]["shares"] for c in only_b}})
    nxt = holdings_of(new["cik"], first_after, contact)
    if nxt is not None:
        for c in sorted(keys):
            if c in nxt:
                print(f"    합쳐 낸 첫 분기 {first_after['period']}: {c} {nxt[c]['name'][:28]} {nxt[c]['shares']:,}주")
            else:
                print(f"    합쳐 낸 첫 분기 {first_after['period']}: {c} 없음")
    report["overlap"] = {"periods": rows_out,
                         "next": {c: (nxt or {}).get(c, {}).get("shares") for c in keys},
                         "next_period": first_after["period"]}


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
