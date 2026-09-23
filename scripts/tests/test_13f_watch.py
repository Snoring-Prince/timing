import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import watch_13f as watch  # noqa: E402
from fetch_sectors import issuer_names  # noqa: E402
from fetch_tickers import wanted_tickers  # noqa: E402
from titans.registry import books, load, one  # noqa: E402
from titans.sec import form_rows, recent_filings  # noqa: E402


class RegistryTests(unittest.TestCase):
    def test_registry_is_the_source_for_active_investors(self):
        investors = load()
        self.assertIn("berkshire", [investor.slug for investor in investors])
        self.assertEqual(one("berkshire").cik, "0001067983")
        self.assertEqual(one("berkshire").output.name, "berkshire.json")

    def test_registry_matches_the_investor_page_settings(self):
        for investor in load():
            with self.subTest(investor=investor.slug):
                html = (SCRIPTS.parent / "titans" / investor.slug / "index.html").read_text(
                    encoding="utf-8")
                self.assertIn(f'slug : "{investor.slug}"', html)
                self.assertIn(f'cik  : "{investor.cik}"', html)
                self.assertIn(f'data : "../../data/titans/{investor.slug}.json"', html)
                self.assertIn(f'since: {investor.since}', html)
                self.assertIn(investor.name["en"], html)
                self.assertIn(investor.name["ko"], html)

    def test_registry_rejects_duplicate_slug_and_bad_cik(self):
        rows = [
            {"slug": "sample", "cik": "123", "filing_name": "One",
             "name": {"en": "One", "ko": "하나"}, "since": 2000},
            {"slug": "sample", "cik": "0000000002", "filing_name": "Two",
             "name": {"en": "Two", "ko": "둘"}, "since": 2000},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "investors.json"
            path.write_text(json.dumps({"investors": rows}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load(path)

    def test_books_reads_every_registered_investor_file(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            first.write_text(json.dumps({"quarters": [{"period": "one"}]}), encoding="utf-8")
            second.write_text(json.dumps({"quarters": [{"period": "two"}]}), encoding="utf-8")
            investors = [SimpleNamespace(output=first), SimpleNamespace(output=second)]
            self.assertEqual([book["quarters"][0]["period"] for book in books(investors)],
                             ["one", "two"])

    def test_shared_helpers_combine_investors_and_keep_the_newest_name(self):
        old = {"quarters": [{"period": "2025-12-31", "holdings": [
            {"cusip": "H1467J104", "name": "OLD CHUBB"},
            {"cusip": "123456789", "name": "OLD ISSUER"},
        ]}]}
        new = {"quarters": [{"period": "2026-03-31", "holdings": [
            {"cusip": "H1467J104", "name": "CHUBB LIMITED"},
            {"cusip": "123456700", "name": "NEW ISSUER"},
        ]}]}
        wanted, names = wanted_tickers([new, old])
        self.assertEqual(wanted, {"H1467J104"})
        self.assertEqual(names["H1467J104"], "CHUBB LIMITED")
        self.assertEqual(issuer_names([new, old])["123456"], "NEW ISSUER")


class SecListTests(unittest.TestCase):
    def test_form_rows_filters_forms_and_tolerates_short_arrays(self):
        block = {
            "form": ["10-K", "13F-HR", "13F-HR/A"],
            "filingDate": ["x", "2026-05-15"],
            "reportDate": ["x", "2026-03-31", "2026-03-31"],
            "accessionNumber": ["x", "regular", "amendment"],
        }
        self.assertEqual(form_rows(block), [
            {"form": "13F-HR", "filed": "2026-05-15",
             "period": "2026-03-31", "accession": "regular"},
            {"form": "13F-HR/A", "filed": None,
             "period": "2026-03-31", "accession": "amendment"},
        ])

    def test_recent_filings_uses_only_current_submission_file(self):
        calls = []

        def fake_get(url, contact):
            calls.append((url, contact))
            return json.dumps({"filings": {"recent": {
                "form": ["13F-HR"], "filingDate": ["2026-05-15"],
                "reportDate": ["2026-03-31"],
                "accessionNumber": ["0001"],
            }}}).encode()

        rows = recent_filings("0000000001", "owner@example.com", fake_get)
        self.assertEqual(len(calls), 1)
        self.assertIn("CIK0000000001.json", calls[0][0])
        self.assertEqual(rows[0]["accession"], "0001")


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "sample.json"
        self.alert = Path(self.temp.name) / "amend-alert.txt"
        self.investor = SimpleNamespace(
            slug="sample", cik="0000000001", filing_name="Sample Manager",
            name={"en": "Sample", "ko": "샘플"}, since=2000,
            output=self.output,
        )
        self.output.write_text(json.dumps({"quarters": [{
            "accession": "known-regular", "amended_by": ["known-amendment"],
        }]}), encoding="utf-8")

    def run_watch(self, rows, argv=None, collector_result=0):
        with mock.patch.dict(os.environ, {"SEC_CONTACT": "owner@example.com"}), \
             mock.patch.object(watch, "ALERT", self.alert), \
             mock.patch.object(watch, "load", return_value=[self.investor]), \
             mock.patch.object(watch, "recent_filings", return_value=rows), \
             mock.patch.object(watch.fetch_13f, "main", return_value=collector_result) as collect:
            result = watch.main(argv or [])
        return result, collect

    def test_known_regular_and_amendment_do_not_trigger_collector(self):
        rows = [
            {"form": "13F-HR", "period": "2025-12-31",
             "filed": "2026-02-14", "accession": "known-regular"},
            {"form": "13F-HR/A", "period": "2025-12-31",
             "filed": "2026-02-15", "accession": "known-amendment"},
        ]
        result, collect = self.run_watch(rows)
        self.assertEqual(result, 0)
        collect.assert_not_called()

    def test_new_accession_runs_only_that_investor_collector(self):
        rows = [{"form": "13F-HR", "period": "2026-03-31",
                 "filed": "2026-05-15", "accession": "new-regular"}]
        result, collect = self.run_watch(rows)
        self.assertEqual(result, 0)
        collect.assert_called_once_with("sample")

    def test_weekly_verification_runs_without_a_new_accession(self):
        rows = [{"form": "13F-HR", "period": "2025-12-31",
                 "filed": "2026-02-14", "accession": "known-regular"}]
        result, collect = self.run_watch(rows, ["--verify-all"])
        self.assertEqual(result, 0)
        collect.assert_called_once_with("sample")

    def test_collector_failure_becomes_workflow_failure(self):
        rows = [{"form": "13F-HR", "period": "2025-12-31",
                 "filed": "2026-02-14", "accession": "known-regular"}]
        result, collect = self.run_watch(rows, ["--verify-all"], collector_result=1)
        self.assertEqual(result, 1)
        collect.assert_called_once_with("sample")


if __name__ == "__main__":
    unittest.main()
