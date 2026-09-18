import datetime as dt
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT))
spec = importlib.util.spec_from_file_location("prices", SCRIPT / "fetch_prices.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def chart(currency="USD", symbol="AAPL", closes=None):
    dates = ["2026-09-16", "2026-09-17", "2026-09-18"]
    return {"chart": {"result": [{"meta": {"currency": currency, "symbol": symbol},
        "timestamp": [int(dt.datetime.fromisoformat(d+"T13:30:00+00:00").timestamp()) for d in dates],
        "indicators": {"quote": [{"close": closes or [100, 101, 102]}],
                       "adjclose": [{"adjclose": [80, 81, 82]}]}}], "error": None}}


class PricesTests(unittest.TestCase):
    def test_pre_1970_listing_dates_work_on_windows(self):
        self.assertEqual(p.from_epoch(-252460800).date(), dt.date(1962, 1, 1))

    def test_closing_prices_exclude_current_bar_before_evening_and_use_no_dividends(self):
        values, _ = p.parse_chart(chart(), "AAPL", dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC))
        self.assertEqual(values, [("2026-09-16", 100), ("2026-09-17", 101)])
        values, _ = p.parse_chart(chart(), "AAPL", dt.datetime(2026, 9, 19, 1, tzinfo=p.UTC))
        self.assertEqual(values[-1], ("2026-09-18", 102))

    def test_currency_symbol_and_invalid_prices(self):
        for payload in [chart(currency="EUR"), chart(symbol="GOOG")]:
            with self.assertRaises(ValueError):
                p.parse_chart(payload, "AAPL", dt.datetime(2026, 9, 19, 1, tzinfo=p.UTC))
        values, _ = p.parse_chart(chart(closes=[None, -1, 102]), "AAPL", dt.datetime(2026, 9, 19, 1, tzinfo=p.UTC))
        self.assertEqual(values, [("2026-09-18", 102)])

    def test_incremental_merge_retains_history_and_overwrites_recent_corrections(self):
        old = {"values": [["2012-01-03", 10], ["2026-09-16", 100]], "splits": {}}
        got = p.merge_series(old, [("2026-09-16", 101), ("2026-09-17", 102)], {}, "2011-01-01", False)
        self.assertEqual(got["values"], [["2012-01-03", 10], ["2026-09-16", 101], ["2026-09-17", 102]])

    def test_changed_split_basis_requires_full_refresh_and_truncation_is_rejected(self):
        old = {"values": [[f"2025-01-{i:02d}", 100] for i in range(1, 21)], "splits": {}}
        with self.assertRaises(ValueError):
            p.merge_series(old, [("2026-09-17", 50)], {"2026-09-17": "2:1"}, "2011-01-01", False)
        with self.assertRaises(ValueError):
            p.merge_series(old, [("2026-09-17", 50)], {}, "2011-01-01", True)
        with self.assertRaises(ValueError):
            p.merge_series(old, [("2025-01-01", 50)], {}, "2011-01-01", True)

    def test_investor_books_share_cache_but_share_classes_remain_separate(self):
        h = lambda c: {"cusip": c, "shares": 10, "value": 100, "name": "Issuer", "class": "CL A"}
        books = [{"quarters": [{"period": "2025-12-31", "holdings": [h("123456100")]},
                                {"period": "2026-03-31", "holdings": [h("123456200")]}]},
                 {"quarters": [{"period": "2026-03-31", "holdings": [h("123456200"), h("123456300")]}]}]
        self.assertEqual(set(p.required_cusips(books)), {"123456200", "123456300"})

    def test_failed_download_keeps_saved_series(self):
        old = {"series": {"123456100": {"ticker": "OLD", "values": [["2026-09-17", 100]], "splits": {}}}}
        with patch.object(p, "request", side_effect=ValueError("offline")), patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old,
                                       dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC))
        self.assertEqual(result["series"], old["series"])
        self.assertEqual(len(errors), 1)

    def test_foreign_ticker_fallback_does_not_guess_between_share_classes(self):
        required = {"G12345100": {"name": "Issuer", "class": "CL A"}}
        with patch.object(p, "request", return_value=[{}]) as req:
            self.assertEqual(p.resolve(list(required), required, {"G12345100": "GUESS"}), {})
            self.assertEqual(req.call_count, 1)

    def test_mapping_outage_does_not_block_existing_ticker_updates(self):
        previous = {"series": {"123456100": {"ticker": "AAPL", "values": [["2026-09-15", 99]], "splits": {}}}}
        required = {c: {"name": "Issuer", "class": "COM"} for c in ["123456100", "654321100"]}
        with patch.object(p, "resolve", side_effect=ValueError("offline")), patch.object(p, "request", return_value=chart()), patch.object(p.time, "sleep"):
            result, errors = p.collect(required, previous, dt.datetime(2026, 9, 19, 1, tzinfo=p.UTC))
        self.assertEqual(result["series"]["123456100"]["values"][-1], ["2026-09-18", 102])
        self.assertNotIn("654321100", result["series"])
        self.assertEqual(len(errors), 2)

    def test_new_split_downloads_all_history_instead_of_mixing_price_bases(self):
        payload = chart(closes=[50, 50.5, 51])
        row = payload["chart"]["result"][0]
        row["events"] = {"splits": {"new": {"date": row["timestamp"][-1], "numerator": 2, "denominator": 1}}}
        old = {"series": {"123456100": {"ticker": "AAPL", "values": [["2026-09-16", 100], ["2026-09-17", 101]], "splits": {}}}}
        with patch.object(p, "request", return_value=payload) as req, patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old,
                                       dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC))
        self.assertEqual(errors, [])
        self.assertEqual(req.call_count, 2)
        self.assertEqual(result["series"]["123456100"]["values"][0][1], 50)
        self.assertEqual(result["series"]["123456100"]["splits"], {"2026-09-18": "2:1"})

    def test_february_anniversary_and_winter_close_cutoff(self):
        self.assertEqual(p.years_before(dt.date(2024, 2, 29)), dt.date(2009, 2, 28))
        # 00:30 UTC is only 19:30 ET during standard time, still before cutoff.
        now = dt.datetime(2026, 1, 9, 0, 30, tzinfo=p.UTC)
        payload = chart()
        row = payload["chart"]["result"][0]
        row["timestamp"] = [int(dt.datetime(2026, 1, day, 14, 30, tzinfo=p.UTC).timestamp()) for day in [6, 7, 8]]
        values, _ = p.parse_chart(payload, "AAPL", now)
        self.assertEqual(values[-1][0], "2026-01-07")
