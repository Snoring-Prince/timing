"""Load and validate the one investor registry used by collectors and pages."""
from dataclasses import dataclass
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/titans/investors.json"


@dataclass(frozen=True)
class Investor:
    slug: str
    cik: str
    filing_name: str
    name: dict
    since: int
    active: bool = True
    # 같은 포트폴리오를 예전에 다른 CIK 로 내던 법인 — ((CIK, 공시 법인명), ...).
    # 공시를 멈춘 번호라 수집기가 한 번에 이어 붙이고, 감시기는 지금 번호만 봅니다
    # (테퍼 — CLAUDE.md 9-3).
    predecessors: tuple = ()
    # 예전 번호 중 **같은 분기를 지금 번호와 둘 다 낸** 것을 합칠 번호들.
    # 기본은 "겹치면 지금 번호가 이긴다"(테퍼). 애크먼은 지주회사(지금 번호)가
    # 2025~2026년 1분기에 자기 몫 하워드 휴즈만 따로 냈고 펀드 몫은 예전 번호가
    # 냈다 — 서로 다른 주머니라 더해야 한다(정찰 6차, CLAUDE.md 9-3).
    merge_overlap: tuple = ()

    @property
    def output(self):
        return ROOT / f"data/titans/{self.slug}.json"


def load(path=REGISTRY):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    investors = []
    seen_slugs = set()
    seen_ciks = set()
    for row in raw.get("investors", []):
        inv = Investor(**row)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", inv.slug):
            raise ValueError(f"invalid investor slug: {inv.slug!r}")
        if not re.fullmatch(r"\d{10}", inv.cik):
            raise ValueError(f"{inv.slug}: CIK must have ten digits")
        if (inv.slug in seen_slugs or inv.cik in seen_ciks or not inv.filing_name
                or not all(inv.name.get(k) for k in ("en", "ko"))):
            raise ValueError(f"invalid or duplicate investor: {inv.slug}")
        # (CIK, 공시 법인명) 짝의 튜플로 둡니다.
        pairs = tuple((str(o.get("cik") or ""), str(o.get("filing_name") or ""))
                      for o in (row.get("predecessors") or ()))
        for ocik, oname in pairs:
            if not re.fullmatch(r"\d{10}", ocik) or ocik == inv.cik or ocik in seen_ciks or not oname:
                raise ValueError(f"{inv.slug}: invalid predecessor {ocik!r}")
            seen_ciks.add(ocik)
        merge = tuple(str(o.get("cik")) for o in (row.get("predecessors") or ())
                      if o.get("merge") is True)
        for o in (row.get("predecessors") or ()):
            if "merge" in o and not isinstance(o["merge"], bool):
                raise ValueError(f"{inv.slug}: predecessor merge must be true/false")
        inv = Investor(**{**row, "predecessors": pairs, "merge_overlap": merge})
        if not 1994 <= inv.since <= 2100:
            raise ValueError(f"{inv.slug}: invalid first year")
        seen_slugs.add(inv.slug)
        seen_ciks.add(inv.cik)
        if inv.active:
            investors.append(inv)
    if not investors:
        raise ValueError("investor registry is empty")
    return investors


def one(slug, path=REGISTRY):
    for inv in load(path):
        if inv.slug == slug:
            return inv
    raise ValueError(f"unknown investor: {slug}")


# Warrants and rights are reported as SH rows under the issuer's own CUSIP prefix,
# so without this they were added to the common stock's shares and value (Oaktree
# 2026Q2: Alvotech warrants were 75% of the "ALVO" row). The pattern matches the 13F
# class strings actually seen — WARRANT, *W EXP mm/dd/yy, W EXP, EQUITY WRT, RIGHT —
# and nothing else in any saved book (2026-11-23). Units and trust units stay shares.
# Keep this identical to isShare() in titans/shared/investor.js and overview.js.
NON_SHARE = re.compile(r"\bWARRANTS?\b|\bWRTS?\b|\bWTS?\b|\bW EXP\b|\bRIGHTS?\b|\bRTS?\b")


def is_share(holding):
    """Options name underlying shares; PRN names principal, not share counts;
    warrants and rights are not the company's shares either."""
    return (str(holding.get("type") or "SH").strip().upper() == "SH"
            and not str(holding.get("putCall") or "").strip()
            and not NON_SHARE.search(str(holding.get("class") or "").upper()))


def books(investors=None, *, strict=False):
    """Read active books; destructive cache pruning requires a complete set."""
    result = []
    for investor in investors if investors is not None else load():
        if not investor.output.exists():
            if strict:
                raise ValueError(f"missing investor book: {investor.output}")
            continue
        book = json.loads(investor.output.read_text(encoding="utf-8"))
        saved_raw = str((book.get("manager") or {}).get("cik") or "")
        saved_cik = saved_raw.zfill(10) if saved_raw else ""
        if saved_cik and hasattr(investor, "cik") and saved_cik != investor.cik:
            raise ValueError(f"{investor.slug}: saved book belongs to CIK {saved_cik}")
        if book.get("quarters"):
            result.append(book)
        elif strict:
            raise ValueError(f"empty investor book: {investor.output}")
    return result
