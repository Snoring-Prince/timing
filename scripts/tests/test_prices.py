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

    def test_full_refresh_scans_splits_from_listing_but_stores_only_the_window(self):
        # 15년 창 밖의 분할이 실려 오고, 옛 종가는 저장되지 않는다.
        now = dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC)
        dates = ["1985-06-03", "2026-09-16", "2026-09-17", "2026-09-18"]
        payload = chart()
        row = payload["chart"]["result"][0]
        row["timestamp"] = [int(dt.datetime.fromisoformat(d+"T13:30:00+00:00").timestamp()) for d in dates]
        row["indicators"]["quote"][0]["close"] = [5, 100, 101, 102]
        row["events"] = {"splits": {"old": {"date": row["timestamp"][0], "numerator": 3, "denominator": 1}}}
        # 이 흉내 응답은 바가 네 개뿐이라 상장일을 주면 길이 검사에 걸린다.
        with patch.object(p, "resolve", return_value={"123456100": "AAPL"}), \
                patch.object(p, "request", return_value=payload) as req, patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, {}, now,
                                       since={"123456100": "1985-06-03"})
        self.assertEqual(errors, [])
        asked = int(dt.datetime.combine(dt.date(1985, 6, 3), dt.time(), p.NY).timestamp())
        self.assertIn(f"period1={asked}", req.call_args[0][0])
        row = result["series"]["123456100"]
        # 마지막 날은 아직 장중이라 빠진다(기존 컷오프). 1985 년 바는 창 밖이라 빠진다.
        self.assertEqual([day for day, _ in row["values"]], dates[1:3])
        self.assertEqual(row["splits"], {"1985-06-03": "3:1"})
        self.assertEqual(row["splitsFrom"], "1985-06-03")

    def test_depth_comes_from_the_first_filing_that_holds_it(self):
        books = [{"quarters": [{"period": "2005-03-31", "holdings": [{"cusip": "A"}, {"cusip": "B"}]},
                               {"period": "2001-06-30", "holdings": [{"cusip": "A"}]}]},
                 {"quarters": [{"period": "2015-12-31", "holdings": [{"cusip": "B"}, {"cusip": "C"}]}]}]
        self.assertEqual(p.first_seen(books), {"A": "2001-06-30", "B": "2005-03-31", "C": "2015-12-31"})

    def test_an_older_investor_joining_later_makes_us_dig_again(self):
        # 1998년부터 들고 있던 투자자가 나중에 등록되면, 2011년까지만 훑어 둔
        # 종목도 그만큼 더 파야 한다. 표식만 보고 넘기면 영영 추측으로 남는다.
        now = dt.datetime(2026, 9, 19, 19, tzinfo=p.UTC)          # 토요일 = 전체 재수집
        old = {"series": {"123456100": {"ticker": "AAPL", "splitsFrom": "2011-09-12",
                                        "values": [["2026-09-16", 100], ["2026-09-17", 101]],
                                        "splits": {}}}}
        with patch.object(p, "resolve", return_value={"123456100": "AAPL"}), \
                patch.object(p, "request", return_value=chart()) as req, patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old, now,
                                       since={"123456100": "1998-12-31"})
        self.assertEqual(errors, [])
        asked = int(dt.datetime.combine(dt.date(1998, 12, 31), dt.time(), p.NY).timestamp())
        self.assertIn(f"period1={asked}", req.call_args[0][0])
        self.assertEqual(result["series"]["123456100"]["splitsFrom"], "1998-12-31")

    def test_a_newcomer_still_gets_the_full_fifteen_year_window(self):
        # 올해 처음 들어온 종목이라고 올해치만 받으면 가격선이 토막난다.
        now = dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC)
        with patch.object(p, "resolve", return_value={"123456100": "AAPL"}), \
                patch.object(p, "request", return_value=chart()) as req, patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, {}, now,
                                       since={"123456100": "2026-06-30"})
        self.assertEqual(errors, [])
        window = p.years_before(dt.date(2026, 9, 18))-dt.timedelta(days=7)
        self.assertIn(f"period1={int(dt.datetime.combine(window, dt.time(), p.NY).timestamp())}",
                      req.call_args[0][0])
        self.assertEqual(result["series"]["123456100"]["splitsFrom"], window.isoformat())

    def test_a_scanned_ticker_does_not_redownload_forty_years_every_week(self):
        # 옛 분할은 변하지 않는다. 이미 훑어 둔 종목은 주 1회 전체 재수집에서도
        # 15년 창만 받고, 창 밖 분할은 저장된 책에서 되살린다.
        saturday = dt.datetime(2026, 9, 19, 19, tzinfo=p.UTC)
        self.assertEqual(saturday.weekday(), 5)
        old = {"series": {"123456100": {"ticker": "AAPL", "splitsFrom": "1985-06-03",
                                        "values": [["2026-09-16", 100], ["2026-09-17", 101]],
                                        "splits": {"1985-06-03": "3:1"}}}}
        with patch.object(p, "resolve", return_value={"123456100": "AAPL"}), \
                patch.object(p, "request", return_value=chart()) as req, patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old, saturday,
                                       since={"123456100": "1985-06-03"})
        self.assertEqual((errors, req.call_count), ([], 1))
        asked = int(dt.datetime.combine(
            p.years_before(dt.date(2026, 9, 19))-dt.timedelta(days=7), dt.time(), p.NY).timestamp())
        deep = int(dt.datetime.combine(dt.date(1985, 6, 3), dt.time(), p.NY).timestamp())
        self.assertIn(f"period1={asked}", req.call_args[0][0])
        self.assertNotIn(f"period1={deep}", req.call_args[0][0])
        row = result["series"]["123456100"]
        self.assertEqual(row["splits"], {"1985-06-03": "3:1"})
        self.assertEqual(row["splitsFrom"], "1985-06-03")

    def test_a_renamed_ticker_is_scanned_from_listing_again(self):
        # 표식은 그 티커의 것이다. 종목이 바뀌면 남의 분할을 물려받으면 안 된다.
        old = {"series": {"123456100": {"ticker": "OLD", "splitsFrom": "1985-06-03",
                                        "values": [["2026-09-16", 100]], "splits": {"1985-06-03": "3:1"}}}}
        with patch.object(p, "resolve", return_value={"123456100": "AAPL"}), \
                patch.object(p, "request", return_value=chart()), patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old,
                                       dt.datetime(2026, 9, 19, 19, tzinfo=p.UTC))
        self.assertEqual(errors, [])
        self.assertEqual(result["series"]["123456100"]["splits"], {})

    def test_incremental_run_keeps_the_deep_scan_marker_and_old_splits(self):
        old = {"series": {"123456100": {"ticker": "AAPL", "splitsFrom": "1985-06-03",
                                        "values": [["2026-09-16", 100]], "splits": {"1985-06-03": "3:1"}}}}
        with patch.object(p, "request", return_value=chart()) as req, patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old,
                                       dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC))
        self.assertEqual((errors, req.call_count), ([], 1))
        row = result["series"]["123456100"]
        self.assertEqual(row["splitsFrom"], "1985-06-03")
        self.assertEqual(row["splits"], {"1985-06-03": "3:1"})

    def test_a_gutted_window_is_rejected_even_when_the_old_bars_are_plentiful(self):
        # 상장 때부터 받으면 옛 바가 많아 "바가 몇 개냐"는 그물이 헐거워진다.
        # 세는 자리는 **저장하는 15년 창 안**이어야 한다.
        now = dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC)
        days = [f"1985-06-{n:02d}" for n in range(1, 21)] + ["2026-09-16", "2026-09-17"]
        payload = chart()
        row = payload["chart"]["result"][0]
        row["timestamp"] = [int(dt.datetime.fromisoformat(d+"T13:30:00+00:00").timestamp()) for d in days]
        row["indicators"]["quote"][0]["close"] = [5]*20 + [101, 102]
        kept = [[f"2026-09-{n:02d}", 100+n] for n in range(2, 17)]
        old = {"series": {"123456100": {"ticker": "AAPL", "values": kept, "splits": {}}}}
        with patch.object(p, "resolve", return_value={"123456100": "AAPL"}), \
                patch.object(p, "request", return_value=payload), patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old, now, full=True)
        self.assertEqual(len(errors), 1)
        self.assertIn("unexpectedly shorter", errors[0])
        self.assertEqual(result["series"]["123456100"]["values"], kept)

    def test_february_anniversary_and_winter_close_cutoff(self):
        self.assertEqual(p.years_before(dt.date(2024, 2, 29)), dt.date(2009, 2, 28))
        # 00:30 UTC is only 19:30 ET during standard time, still before cutoff.
        now = dt.datetime(2026, 1, 9, 0, 30, tzinfo=p.UTC)
        payload = chart()
        row = payload["chart"]["result"][0]
        row["timestamp"] = [int(dt.datetime(2026, 1, day, 14, 30, tzinfo=p.UTC).timestamp()) for day in [6, 7, 8]]
        values, _ = p.parse_chart(payload, "AAPL", now)
        self.assertEqual(values[-1][0], "2026-01-07")
