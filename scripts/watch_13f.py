#!/usr/bin/env python3
"""Lightweight watcher: run the full collector only for changed investors."""
import argparse
import json
import os
from pathlib import Path

import fetch_13f
from titans.registry import load
from titans.sec import recent_filings

ALERT = Path("amend-alert.txt")


def known_accessions(path):
    if not Path(path).exists():
        return set()
    book = json.loads(Path(path).read_text(encoding="utf-8"))
    known = {q["accession"] for q in book.get("quarters", []) if q.get("accession")}
    known.update(a for q in book.get("quarters", []) for a in q.get("amended_by", []))
    return known


def changed(investor, rows):
    known = known_accessions(investor.output)
    return [row for row in rows if row["accession"] not in known]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-all", action="store_true",
                        help="run every collector even when no new accession is visible")
    args = parser.parse_args(argv)
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        print("받을 수 없습니다: 비밀값 SEC_CONTACT 가 없습니다.")
        return 1
    ALERT.unlink(missing_ok=True)
    selected, errors = [], []
    for investor in load():
        try:
            rows = recent_filings(investor.cik, contact)
            new = changed(investor, rows)
            print(f"{investor.slug}: 최신 목록 {len(rows)}건 · 새 접수 {len(new)}건")
            if args.verify_all or new:
                selected.append(investor)
                for row in new:
                    print(f"  {row['form']} {row['period']} {row['accession']}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{investor.slug}: 공시 감시 실패: {exc}")
    for investor in selected:
        try:
            if fetch_13f.main(investor.slug):
                errors.append(f"{investor.slug}: 공시 수집 실패")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{investor.slug}: 공시 수집 중 예외: {exc}")
    if not selected:
        print("새 공시 없음: 무거운 원문 수집을 실행하지 않습니다.")
    if errors:
        print("\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
