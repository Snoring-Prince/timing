#!/usr/bin/env python3
"""거장들의 선택 요약 — 목록 화면(/titans/)과 첫 화면 카드가 받는 작은 파일.

투자자마다 공시책 전체(버크셔는 480KB)를 받지 않고, 최근 공시 한 분기의
총액·종목 수·비중 상위 셋만 담습니다. 공시를 받은 뒤 봇이 다시 만듭니다
(update-13f.yml). **이 파일을 손으로 고치지 마세요** — 다음 실행이 덮어씁니다.

범위는 투자자 화면과 같습니다: 옵션·원금(PRN)을 빼고, 발행사(CUSIP 앞 6자리)로
묶되 우선주는 따로 둡니다. 이름 표기는 화면의 title() 을 그대로 옮긴 것이고,
검사가 두 구현이 같은 글자를 내는지 모든 이름으로 대조합니다.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from titans import registry  # noqa: E402

OUT = registry.ROOT / "data/titans/summary.json"
TOP = 3

ISPFD = re.compile(r"\bPFD\b|PREFERRED")
KEEP = {"IBM", "HP", "NVR", "USA", "US", "UK", "AT&T", "PLC", "LLC", "NV", "SA", "AG",
        "ADR", "REIT", "MTN"}
SMALL = {"of", "and", "the", "for", "de", "la"}


def title(s):
    """investor.js 의 title() 과 같은 규칙. 소문자가 섞인 이름은 그대로 둔다."""
    if re.search(r"[a-z]", s):
        return s
    out = []
    for i, w in enumerate(re.split(r"\s+", s)):
        if re.sub(r"[^A-Z&.]", "", w) in KEEP:
            out.append(w)
            continue
        low = w.lower()
        out.append(low if i > 0 and low in SMALL else w[:1] + low[1:])
    return " ".join(out)


def gkey(h):
    return h["cusip"][:6] + ("|P" if ISPFD.search((h.get("class") or "").upper()) else "")


def summarize(investor, book):
    quarters = book.get("quarters") or []
    if not quarters:
        return None
    q = quarters[-1]
    groups = {}
    for h in q["holdings"]:
        if not registry.is_share(h):
            continue
        g = groups.setdefault(gkey(h), {"name": h["name"], "value": 0})
        g["value"] += h["value"]
    rows = sorted(groups.values(), key=lambda g: -g["value"])
    total = sum(g["value"] for g in rows)
    return {
        "slug": investor.slug,
        "name": investor.name,
        "since": investor.since,
        "period": q["period"],
        "filed": q.get("filed", ""),
        "quarters": len(quarters),
        "total": total,
        "stocks": len(rows),
        "top": [{"name": title(g["name"]), "w": round(g["value"] / total * 100, 1) if total else 0}
                for g in rows[:TOP]],
    }


def build(investors=None):
    items = []
    for investor in investors if investors is not None else registry.load():
        if not investor.output.exists():
            continue
        book = json.loads(investor.output.read_text(encoding="utf-8"))
        item = summarize(investor, book)
        if item:
            items.append(item)
    return {"investors": items}


def main(out=OUT):
    data = build()
    if not data["investors"]:
        raise SystemExit("요약할 공시책이 하나도 없습니다 — 기존 요약을 그대로 둡니다")
    payload = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if out.exists() and out.read_text(encoding="utf-8") == payload:
        print(f"{out.name}: 그대로")
        return
    tmp = out.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(out)
    print(f"{out.name}: {len(data['investors'])}곳 · {len(payload.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    main()
