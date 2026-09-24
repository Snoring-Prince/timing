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


def is_share(holding):
    """Options name underlying shares; PRN names principal, not share counts."""
    return (str(holding.get("type") or "SH").strip().upper() == "SH"
            and not str(holding.get("putCall") or "").strip())


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
