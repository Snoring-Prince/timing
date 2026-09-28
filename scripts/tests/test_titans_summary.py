import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import publish_titans as pt  # noqa: E402
from titans import registry  # noqa: E402

ROOT = SCRIPTS.parent


class SummaryTests(unittest.TestCase):
    def test_berkshire_summary_matches_the_investor_page(self):
        inv = registry.one("berkshire")
        book = json.loads(inv.output.read_text(encoding="utf-8"))
        book["quarters"] = [q for q in book["quarters"] if q["period"] <= "2026-06-30"]
        s = pt.summarize(inv, book)
        # 투자자 화면이 같은 분기에 적는 숫자: 26종목 · 1위 애플 22.0% · 알파벳은 A+C 합쳐 12.6%.
        self.assertEqual((s["period"], s["stocks"]), ("2026-06-30", 26))
        self.assertEqual(s["top"][0], {"name": "Apple Inc", "w": 22.0})
        self.assertEqual(s["top"][2], {"name": "Alphabet Inc", "w": 12.6})
        self.assertEqual(s["quarters"], 111)

    def test_options_principal_and_preferred_follow_the_screen_rules(self):
        common = {"cusip": "123456100", "name": "FIX CORP", "class": "COM", "shares": 1, "value": 300}
        pref = {**common, "cusip": "123456209", "class": "PFD CONV", "value": 100}
        call = {**common, "putCall": "CALL", "value": 5000}
        note = {**common, "type": "PRN", "value": 5000}
        book = {"quarters": [{"period": "2026-06-30", "holdings": [common, pref, call, note]}]}
        s = pt.summarize(SimpleNamespace(slug="x", name={"en": "X", "ko": "X"}, since=2020), book)
        self.assertEqual((s["total"], s["stocks"]), (400, 2))
        self.assertEqual([t["w"] for t in s["top"]], [75.0, 25.0])

    def test_missing_books_are_skipped_and_nothing_at_all_keeps_the_old_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            out = tmp / "summary.json"
            out.write_text("old", encoding="utf-8")
            gone = SimpleNamespace(slug="gone", output=tmp / "gone.json")
            with patch.object(pt.registry, "load", return_value=[gone]), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    pt.main(out)
            self.assertEqual(out.read_text(encoding="utf-8"), "old")

    def test_the_committed_summary_is_what_the_bot_would_write(self):
        # 봇이 공시를 받은 같은 실행에서 요약을 다시 만들므로 늘 같아야 한다.
        saved = json.loads((ROOT / "data/titans/summary.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, pt.build())
        slugs = [i.slug for i in registry.load() if i.output.exists()]
        self.assertEqual([o["slug"] for o in saved["investors"]], slugs)

    def test_the_workflow_rebuilds_the_summary_before_saving(self):
        wf = (ROOT / ".github/workflows/update-13f.yml").read_text(encoding="utf-8")
        self.assertLess(wf.index("scripts/publish_titans.py"), wf.index("git add data/titans/*.json"))


if __name__ == "__main__":
    unittest.main()
