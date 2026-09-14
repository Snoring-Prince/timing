"""
2013년 이전 13F 텍스트 공시 → 요즘 형식.  **한 번 쓰고 끝난 코드입니다.**

2026-09-14 에 한 번 돌려서 58개 분기(1998-12-31 ~ 2013-03-31)를
data/titans/berkshire.json 에 넣었습니다. **다시 돌릴 일이 없습니다** —
그 공시들은 영영 안 바뀝니다. 유지보수하지 마세요. 고치지도 마세요.
남겨 둔 이유는 하나뿐입니다: 나중에 옛 분기 숫자가 의심스러우면
무엇을 어떻게 읽었는지 여기서 확인할 수 있게.

돌린 방법: dump-13f-raw 워크플로가 원본을 raw-13f 브랜치에 올렸고(그 워크플로와
브랜치는 지웠습니다), 이 스크립트가 그 폴더를 읽었습니다.

검산: 각 공시는 스스로 `Form 13F Information Table Value Total` 을 적어 둡니다.
**58개 분기 전부 그 총액과 맞았습니다.** 그것이 이 조잡한 코드를 믿는 근거입니다.

읽으면서 실제로 밟은 함정 다섯 (전부 금액이 어긋나서 드러났습니다):
  · TORCHMARK·SPONSORED 같은 아홉 글자 이름이 CUSIP 으로 잡힘
  · 넓은 정규식이 탐욕적이라 금액 칸 첫 숫자를 물어감 (2,912,308 → 912,308)
  · 숫자 칸이 오른쪽 맞춤이라 자릿수가 크면 시작 위치가 앞으로 밀림
  · `868168 10 F` 처럼 끝이 글자인 CUSIP, `82028k` 처럼 소문자 섞인 것
  · `Entry Total:.` 처럼 콜론 뒤에 마침표가 붙은 판

저장 위치: scripts/onetime/convert_13f_text.py
"""
import json, os, re, sys
from statistics import median

RAW = sys.argv[1]
NUM   = re.compile(r"\(?\$?\s*([\d,]+)\)?")


def nums(s):
    out = []
    for m in NUM.finditer(s):
        t = m.group(1).replace(",", "")
        if t.isdigit():
            out.append(int(t))
    return out


# CUSIP 찾기. **폭을 하나로 넓히면 안 됩니다** — 넓은 정규식은 탐욕적이라
# 금액 칸의 첫 숫자까지 물어갑니다(실제로 025816109 가 0258161096 이 되어
# 2,912,308 이 912,308 으로 읽혔습니다). 그래서 **좁은 것부터 순서대로** 봅니다.
#   6-2-1  보통                      025816 10 9 / 025816109
#   7-2-1  드물게 앞자리가 하나 김   949773V 10 7 (웰포인트, 2007~2009)
# 마지막 자리를 숫자로 못박으면 안 됩니다 — `868168 10 F` 처럼 끝이 글자인
# 줄이 있고, `82028k 20 0` 처럼 소문자도 섞입니다. 둘 다 진짜 보유 종목이라
# 빼면 금액이 어긋납니다(2000-09-30 에서 정확히 그 두 줄이 빠졌습니다).
# 대신 **앞 여섯 자에 숫자가 있을 것**으로 거릅니다 — TORCHMARK·SPONSORED
# 처럼 아홉 글자짜리 이름은 이 조건에서 걸러집니다.
CUSIPS = [re.compile(r"\b([0-9A-Za-z]{6})\s*([0-9A-Za-z]{2})\s*([0-9A-Za-z])\b"),
          re.compile(r"\b([0-9A-Za-z]{7})\s*([0-9A-Za-z]{2})\s*([0-9A-Za-z])\b")]


def cusip_at(line, start=0):
    """진짜 CUSIP 처럼 생긴 첫 자리를 돌려줍니다.

    앞 여섯 자에 숫자가 있어야 하고, **뒤에 큰 숫자가 둘 이상** 따라와야
    합니다 — 자회사 번호 목록이 CUSIP 으로 잡히는 것을 막습니다."""
    for rx in CUSIPS:
        for m in rx.finditer(line, start):
            tok = (m.group(1) + m.group(2) + m.group(3)).upper()
            if not any(c.isdigit() for c in tok[:6]):
                continue
            if len([v for v in nums(line[m.end():]) if v >= 100]) < 2:
                continue
            return m, tok
    return None, None


SKIP  = re.compile(r"^[\s\-=_.<>$|]*$|^<[SC]>|Column \d|Name of|Issuer\s+Class|"
                   r"Title of Class|In Thousands|Discretion|Voting Authority|"
                   r"Sole\s+Shared|\bCUSIP\b|Amount\s|Managers", re.I)

def numcol(s):
    """첫 숫자가 **어디서 끝나는지**. 숫자 칸은 오른쪽 맞춤이라, 자릿수가
    크면 시작은 앞으로 밀리지만 끝은 그대로입니다. 시작으로 맞추면
    금액이 큰 줄을 놓칩니다(실제로 그래서 한두 줄씩 빠졌습니다)."""
    m = NUM.search(s)
    return m.end(1) if m else -1

def parse(txt):
    """표에서 줄을 꺼냅니다. 이름은 여러 줄에 걸쳐 있고, 이어지는 줄에는
    이름·종류·CUSIP 이 비어 있습니다 — 앞 줄 것을 물려받습니다.

    자회사 번호 목록(4, 3, 14, 16, 17, 18)이 줄바꿈되면 숫자 줄처럼 보입니다.
    **고정폭 표이므로 금액 칸의 위치로 거릅니다** — 진짜 데이터 줄은 금액이
    앞 줄과 같은 칸에서 시작합니다."""
    rows, pend, cur, col = [], [], None, -1
    for block in re.findall(r"<TABLE>(.*?)</TABLE>", txt, re.S):
        for raw in block.split("\n"):
            line = raw.rstrip()
            if not line.strip():
                pend = []; continue
            if SKIP.match(line.strip()) and not cusip_at(line)[0]:
                pend = []; continue
            m, tok = cusip_at(line)
            if m:
                head = line[:m.start()]
                parts = [p.strip() for p in re.split(r"\s{2,}", head) if p.strip()]
                cls = parts[-1] if len(parts) >= 2 else ""
                nm  = " ".join(pend + parts[:-1]) if len(parts) >= 2 else " ".join(pend + parts)
                cur = {"name": re.sub(r"\s+", " ", nm).strip(),
                       "class": cls, "cusip": tok}
                pend = []
                tail = line[m.end():]
                v = nums(tail)
                if len(v) >= 2:
                    rows.append(dict(cur, value=v[0], shares=v[1]))
                    c = numcol(tail)
                    col = m.end() + c if c >= 0 else -1
                continue
            v = nums(line)
            c = numcol(line)
            aligned = col >= 0 and abs(c - col) <= 3
            if (len(v) >= 2 and cur and aligned
                    and not line.lstrip().startswith(("$", "-", "="))):
                rows.append(dict(cur, value=v[0], shares=v[1]))
            elif not v:
                pend.append(line.strip())
            else:
                pend = []
    return rows

def fold(rows, scale):
    agg = {}
    for x in rows:
        k = (x["cusip"], x["class"])
        a = agg.setdefault(k, {"cusip": x["cusip"], "name": x["name"],
                               "class": x["class"], "value": 0, "shares": 0, "lines": 0})
        a["value"] += x["value"] * scale; a["shares"] += x["shares"]; a["lines"] += 1
    return sorted(agg.values(), key=lambda a: -a["value"])

idx = json.load(open(os.path.join(RAW, "index.json")))
out, bad = [], []
for f in idx["filings"]:
    d = os.path.join(RAW, f"{f['period']}_{f['accession']}")
    t = sorted(x for x in os.listdir(d) if x.endswith(".txt")) if os.path.isdir(d) else []
    # 폴더에 둘이면 접수번호 이름이 전체 제출본입니다 — 그쪽을 고릅니다.
    t = [x for x in t if x.startswith(f["accession"])] or t
    if not t:
        bad.append((f["period"], f["form"], "txt 없음", 0, 0)); continue
    txt = open(os.path.join(d, t[0]), encoding="utf-8", errors="replace").read()
    ent = [int(x.replace(",", "")) for x in
           re.findall(r"Entry Total:[.\s]*\$?[.\s]*([\d,]+)", txt)]
    val = [int(x.replace(",", "")) for x in
           re.findall(r"Value Total:[.\s]*\$?[.\s]*([\d,]+)", txt)]
    rows = parse(txt)
    if not rows:
        bad.append((f["period"], f["form"], "줄 0개", sum(ent), 0)); continue
    r = [x["value"]/x["shares"] for x in rows if x["shares"] > 0 and x["value"] > 0]
    scale = 1000 if r and median(r) < 1.0 else 1
    held = fold(rows, scale)
    tot = sum(h["value"] for h in held)
    want = sum(val) * scale
    off = abs(tot - want)/want if want else 1
    rec = {"period": f["period"], "form": f["form"], "filed": f["filed"],
           "accession": f["accession"], "lines": len(rows), "entry_total": sum(ent),
           "total": tot, "stated": want, "off": off, "holdings": held}
    out.append(rec)
    if off > 0.005 or (sum(ent) and sum(ent) != len(rows)):
        bad.append((f["period"], f["form"], f"총액 {off:.1%} · 줄 {len(rows)} vs 공시 {sum(ent)}",
                    sum(ent), len(rows)))

def good(r): return r["off"] <= 0.005 and r["entry_total"] == r["lines"]
orig = [r for r in out if r["form"] == "13F-HR"]
amd  = [r for r in out if r["form"] != "13F-HR"]
print(f"파일 {len(idx['filings'])}건 · 읽은 것 {len(out)}건\n")
print(f"원본(13F-HR)  {len(orig)}건 중 정확 {sum(1 for r in orig if good(r))}건")
print(f"정정(13F-HR/A) {len(amd)}건 중 정확 {sum(1 for r in amd if good(r))}건\n")
print("원본 중 안 맞는 것:")
nb = [r for r in orig if not good(r)]
for r in nb[:20]:
    print(f"  {r['period']}  총액 {r['off']:>6.1%} · 줄 {r['lines']:>3} vs 공시 {r['entry_total']:>3}")
if len(nb) > 20: print(f"  … 그 밖 {len(nb)-20}건")
ok = [r for r in out if good(r)]
print(f"\n완전히 맞는 것 {len(ok)}건")
for r in ok[:3] + ok[-3:]:
    print(f"  {r['period']}  {r['form']:<9} 줄{r['lines']:>4} → 종목{len(r['holdings']):>3}  "
          f"${r['total']/1e9:>7.1f}B  (공시 ${r['stated']/1e9:.1f}B)")
json.dump(out, open(os.path.join(RAW, "..", "converted.json"), "w"), ensure_ascii=False)
