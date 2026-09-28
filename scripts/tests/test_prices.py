import contextlib
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
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
        # 종류 글자가 적힌 줄은 로고용 옛 티커(GUESS)를 쓰지 않고 이름 검색만 한다.
        required = {"G12345100": {"name": "Issuer", "class": "CL A"}}
        with patch.object(p, "request", return_value=[{}]) as req, patch("builtins.print"):
            self.assertEqual(p.resolve(list(required), required, {"G12345100": "GUESS"}), {})
        self.assertEqual([c.args[0].rsplit("/", 1)[-1] for c in req.call_args_list], ["mapping", "search"])

    def test_ny_registry_shares_map_through_the_verified_ticker(self):
        # ASML(네덜란드)은 미국에서 본주 그대로 '뉴욕 등록주'로 거래된다.
        # CINS 로는 OpenFIGI 가 모르고, 옛 규칙은 'COM' 만 받아서 떨어졌다.
        required = {"N07059210": {"name": "ASML HLDG NV", "class": "N Y REGISTRY SHS"}}
        # 러너가 받은 OpenFIGI 응답 그대로(2026-09-28, Update Titans Prices #9 로그).
        # 첫 판은 이 모양을 짐작으로 적어서(이름 'ASML HOLDING NV') 검사는 통과하고
        # 실제로는 떨어졌다 — 짐작한 응답으로 짠 검사는 짐작을 검사할 뿐이다.
        row = {"figi": "BBG000K6MRN4", "name": "ASML HOLDING NV-NY REG SHS", "ticker": "ASML",
               "exchCode": "US", "compositeFIGI": "BBG000K6MRN4", "securityType": "NY Reg Shrs",
               "marketSector": "Equity", "shareClassFIGI": "BBG001SCG0R3",
               "securityType2": "Depositary Receipt", "securityDescription": "ASML"}
        with patch.object(p, "request", side_effect=[[{}], [{"data": [row]}]]):
            self.assertEqual(p.resolve(list(required), required, {"N07059210": "ASML"}), {"N07059210": "ASML"})

    def test_registry_fallback_still_refuses_adrs_classes_and_other_names(self):
        required = {"N07059210": {"name": "ASML HLDG NV", "class": "N Y REGISTRY SHS"}}
        adr = {"ticker": "ASML", "name": "ASML HOLDING NV", "securityType": "ADR",
               "securityType2": "Depositary Receipt", "shareClassFIGI": "X"}
        other = {"ticker": "ASML", "name": "ASM INTERNATIONAL NV-NY REG SHS", "securityType": "NY Reg Shrs",
                 "securityType2": "Depositary Receipt", "shareClassFIGI": "Y"}
        for bad in (adr, other):
            with patch.object(p, "request", side_effect=[[{}], [{"data": [bad]}]]):
                self.assertEqual(p.resolve(list(required), required, {"N07059210": "ASML"}), {})
        for cls in ("SHS CL A", "ORD SHS CL A", "SPONSORED ADR", "PFD SHS", "UNIT 12/20/2025"):
            with self.subTest(cls=cls):
                req = {"N07059210": {"name": "ASML HLDG NV", "class": cls}}
                with patch.object(p, "request", return_value=[{}]) as call, patch("builtins.print"):
                    self.assertEqual(p.resolve(list(req), req, {"N07059210": "ASML"}), {})
                # 옛 티커로 묻는 길(TICKER)은 어느 것도 안 탄다. 종류 글자 줄만 이름 검색.
                asked = [c.args[0].rsplit("/", 1)[-1] for c in call.call_args_list]
                self.assertEqual(asked, ["mapping", "search"] if "CL A" in cls else ["mapping"])

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

    def test_a_sold_holding_leaves_the_visitor_file(self):
        # 방문자가 받는 파일에 안 쓰는 종목을 쌓지 않는다. 화면이 읽는 것은
        # 지금 보유 종목뿐이라, 팔린 종목의 종가는 한 번도 안 읽힌다.
        old = {"series": {"123456100": {"ticker": "AAPL", "values": [["2026-09-16", 100]], "splits": {}},
                          "999999100": {"ticker": "GONE", "values": [["2026-09-16", 50]], "splits": {}}}}
        with patch.object(p, "request", return_value=chart()), patch.object(p.time, "sleep"):
            result, errors = p.collect({"123456100": {"name": "Issuer", "class": "COM"}}, old,
                                       dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC))
        self.assertEqual(errors, [])
        self.assertEqual(list(result["series"]), ["123456100"])

    def test_a_re_entry_is_scanned_from_its_first_filing_again(self):
        # 팔면서 버렸으므로 다시 들어오면 파일에 없다. 그때는 새 종목과 같은
        # 길로 **처음 공시 분기까지** 다시 훑는다(요청 1번).
        now = dt.datetime(2026, 9, 18, 19, tzinfo=p.UTC)
        old = {"series": {"123456100": {"ticker": "AAPL", "values": [["2026-09-16", 100]], "splits": {}}}}
        required = {c: {"name": "Issuer", "class": "COM"} for c in ["123456100", "999999100"]}
        with patch.object(p, "resolve", return_value={"999999100": "BACK"}), \
                patch.object(p, "request", return_value=chart(symbol="BACK")) as req, \
                patch.object(p.time, "sleep"):
            result, errors = p.collect(required, old, now,
                                       since={"999999100": "2004-03-31", "123456100": "2004-03-31"})
        asked = int(dt.datetime.combine(dt.date(2004, 3, 31), dt.time(), p.NY).timestamp())
        back = [c for c in req.call_args_list if "BACK" in c[0][0]]
        self.assertEqual(len(back), 1)
        self.assertIn(f"period1={asked}", back[0][0][0])
        self.assertEqual(result["series"]["999999100"]["splitsFrom"], "2004-03-31")

    def test_an_unreadable_book_never_empties_the_price_cache(self):
        # 공시책을 한 권도 못 읽으면 보유 목록이 비고, 위 규칙이 파일을 통째로
        # 비운다. 그 전에 멈춰야 한다.
        # **검사는 진짜 파일을 건드리면 안 된다.** 이 가드를 되돌려 확인하는
        # 순간 main() 이 실제 prices.json 을 비워 버린다(실제로 겪었다).
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "prices.json"
            out.write_text('{"series":{"123456100":{}}}', encoding="utf-8")
            with patch.object(p, "books", return_value=[]), patch.object(p, "OUT", out), \
                    patch.object(p.sys, "argv", ["fetch_prices.py"]):
                with self.assertRaises(SystemExit):
                    p.main()
            self.assertIn("123456100", out.read_text(encoding="utf-8"))

    def test_each_investor_file_holds_only_that_investors_latest_holdings(self):
        # 여덟 명이 한 파일을 같이 쓰면 버크셔 화면을 여는 사람도 여덟 명분을
        # 받는다. 투자자 파일에는 **자기 최신 보유**만 들어가야 한다 —
        # 둘이 같이 든 종목은 양쪽에, 옛 분기에만 있던 종목은 어디에도 없다.
        def book(*periods):
            return {"quarters": [{"period": per, "holdings": [
                {"cusip": c, "name": c, "shares": 1, "value": 1} for c in cs]} for per, cs in periods]}
        a = book(("2026-03-31", ["OLD000100"]), ("2026-06-30", ["SHARED100", "ONLYA0100"]))
        b = book(("2026-06-30", ["SHARED100", "ONLYB0100"]))
        cache = {"method": "split-adjusted-close", "series": {
            c: {"ticker": c, "values": [["2026-09-18", 1]]}
            for c in ["SHARED100", "ONLYA0100", "ONLYB0100", "OLD000100"]}}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertEqual(p.publish(cache, [("a", a), ("b", b)], folder), ["a", "b"])
            got = {s: set(json.loads((folder/f"{s}.json").read_text())["series"]) for s in "ab"}
            self.assertEqual(got, {"a": {"SHARED100", "ONLYA0100"}, "b": {"SHARED100", "ONLYB0100"}})
            # 내용이 같으면 다시 쓰지 않는다 — 안 그러면 매일 빈 커밋이 생긴다.
            self.assertEqual(p.publish(cache, [("a", a), ("b", b)], folder), [])

    def test_publish_only_writes_investor_files_without_downloading(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, folder = Path(tmp)/"prices.json", Path(tmp)/"prices"
            out.write_text(json.dumps({"method": "split-adjusted-close", "series": {
                "123456100": {"ticker": "AAPL", "values": [["2026-09-18", 1]]}}}), encoding="utf-8")
            book = {"quarters": [{"period": "2026-06-30", "holdings": [
                {"cusip": "123456100", "name": "A", "shares": 1, "value": 1}]}]}
            inv = type("Inv", (), {"slug": "x", "output": out})()
            with patch.object(p.registry, "load", return_value=[inv]), \
                    patch.object(p, "books", return_value=[book]), patch.object(p, "OUT", out), \
                    patch.object(p, "PER", folder), patch.object(p, "request") as req, \
                    patch.object(p.sys, "argv", ["fetch_prices.py", "--publish"]), \
                    patch("builtins.print"):
                p.main()
            req.assert_not_called()
            self.assertIn("123456100", (folder/"x.json").read_text())

    def test_a_just_registered_investor_waits_but_a_lost_book_still_stops(self):
        # 등록만 하고 공시를 아직 안 받은 투자자(책도 투자자 파일도 없음)는 건너뛴다.
        # 책만 사라지고 투자자 파일이 남아 있으면 예전처럼 멈춘다 — 그걸 전량 매도로
        # 읽고 가격을 지우면 안 된다.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            out, folder = tmp/"prices.json", tmp/"prices"
            folder.mkdir()
            out.write_text(json.dumps({"method": "split-adjusted-close", "series": {
                "123456100": {"ticker": "AAPL", "values": [["2026-09-18", 1]]}}}), encoding="utf-8")
            (tmp/"old.json").write_text(json.dumps({"quarters": [{"period": "2026-06-30",
                "holdings": [{"cusip": "123456100", "name": "A", "shares": 1, "value": 1}]}]}),
                encoding="utf-8")
            Inv = lambda slug: type("Inv", (), {"slug": slug, "output": tmp/f"{slug}.json", "cik": ""})()
            old, new = Inv("old"), Inv("new")
            run = lambda investors: (
                patch.object(p.registry, "load", return_value=investors), patch.object(p, "OUT", out),
                patch.object(p, "PER", folder), patch.object(p, "request"),
                patch.object(p.sys, "argv", ["fetch_prices.py", "--publish"]), patch("builtins.print"))
            with contextlib.ExitStack() as stack:
                req = [stack.enter_context(c) for c in run([old, new])][3]
                p.main()
            req.assert_not_called()
            self.assertTrue((folder/"old.json").exists())
            self.assertFalse((folder/"new.json").exists())
            (folder/"new.json").write_text("{}", encoding="utf-8")
            with contextlib.ExitStack() as stack:
                for c in run([old, new]):
                    stack.enter_context(c)
                with self.assertRaises(ValueError):
                    p.main()

    def test_february_anniversary_and_winter_close_cutoff(self):
        self.assertEqual(p.years_before(dt.date(2024, 2, 29)), dt.date(2009, 2, 28))
        # 00:30 UTC is only 19:30 ET during standard time, still before cutoff.
        now = dt.datetime(2026, 1, 9, 0, 30, tzinfo=p.UTC)
        payload = chart()
        row = payload["chart"]["result"][0]
        row["timestamp"] = [int(dt.datetime(2026, 1, day, 14, 30, tzinfo=p.UTC).timestamp()) for day in [6, 7, 8]]
        values, _ = p.parse_chart(payload, "AAPL", now)
        self.assertEqual(values[-1][0], "2026-01-07")


# 러너가 받은 OpenFIGI 응답 그대로(2026-09-28, Update Titans Prices #12 로그).
# 오크트리의 해외 법인 A주는 이름 끝에 종류 꼬리가 붙어 와서 떨어졌다.
TORM = {"figi": "BBG00JG0MYJ1", "name": "TORM PLC-A", "ticker": "TRMD", "exchCode": "US",
        "compositeFIGI": "BBG00JG0MYJ1", "securityType": "Common Stock", "marketSector": "Equity",
        "shareClassFIGI": "BBG00CJZ1L61", "securityType2": "Common Stock", "securityDescription": "TRMD"}
LBTY = {"figi": "BBG01K9HZH92", "name": "LIBERTY GLOBAL LTD-A", "ticker": "LBTYA", "exchCode": "US",
        "compositeFIGI": "BBG01K9HZH92", "securityType": "Common Stock", "marketSector": "Equity",
        "shareClassFIGI": "BBG01K9HZHB9", "securityType2": "Common Stock", "securityDescription": "LBTYA"}
XP = {"figi": "BBG00QVJYGM9", "name": "XP INC - CLASS A", "ticker": "XP", "exchCode": "US",
      "compositeFIGI": "BBG00QVJYGM9", "securityType": "Common Stock", "marketSector": "Equity",
      "shareClassFIGI": "BBG00QVJYHP4", "securityType2": "Common Stock", "securityDescription": "XP"}


class UnpricedTests(unittest.TestCase):
    def test_class_a_suffix_maps_but_is_left_for_the_price_check(self):
        for cusip, name, ticker, row in (("G89479102", "TORM PLC", "TRMD", TORM),
                                         ("G61188101", "LIBERTY GLOBAL LTD", "LBTYA", LBTY),
                                         ("G98239109", "XP INC", "XP", XP)):
            with self.subTest(ticker=ticker):
                required = {cusip: {"name": name, "class": "COMMON STOCK"}}
                later = set()
                with patch.object(p, "request", side_effect=[[{}], [{"data": [row]}]]):
                    self.assertEqual(p.resolve([cusip], required, {cusip: ticker}, later), {cusip: ticker})
                self.assertEqual(later, {cusip})

    def test_only_the_a_tail_is_dropped(self):
        required = {"G61188127": {"name": "LIBERTY GLOBAL LTD", "class": "COMMON STOCK"}}
        for tail in ("B", "C"):
            row = {**LBTY, "name": f"LIBERTY GLOBAL LTD-{tail}"}
            with patch.object(p, "request", side_effect=[[{}], [{"data": [row]}]]), patch("builtins.print"):
                self.assertEqual(p.resolve(list(required), required, {"G61188127": "LBTYA"}), {})

    def test_a_warrant_does_not_count_as_a_second_share_class_but_two_commons_do(self):
        row = {**TORM, "name": "RICE ACQUISITION CORP 3-A", "ticker": "KRSP"}
        required = {"G7553X106": {"name": "RICE ACQUISITION CORP 3", "class": "COMMON STOCK"},
                    "G7553X114": {"name": "RICE ACQUISITION CORP 3", "class": "WARRANT"}}
        known = {c: "KRSP" for c in required}
        with patch.object(p, "request", side_effect=[[{}, {}], [{"data": [row]}]]):
            self.assertEqual(p.resolve(list(required), required, known), {"G7553X106": "KRSP"})
        # 리버티 라틴아메리카: 같은 회사의 보통주 두 종류(A·C) — 어느 쪽인지 못 가린다.
        both = {"G9001E102": {"name": "LIBERTY LATIN AMERICA LTD", "class": "COMMON STOCK"},
                "G9001E128": {"name": "LIBERTY LATIN AMERICA LTD", "class": "COMMON STOCK"}}
        with patch.object(p, "request", return_value=[{}, {}]) as req:
            self.assertEqual(p.resolve(list(both), both, {c: "LILA" for c in both}), {})
            self.assertEqual(req.call_count, 1)

    def test_abbreviated_truncated_and_com_shs_names_from_baupost(self):
        # 러너 원본 그대로(2026-09-28, Update Titans Prices #16).
        ncl = {"figi": "BBG000BSRN78", "name": "NORWEGIAN CRUISE LINE HOLDIN", "ticker": "NCLH", "exchCode": "US",
               "compositeFIGI": "BBG000BSRN78", "securityType": "Common Stock", "marketSector": "Equity",
               "shareClassFIGI": "BBG001SCKPS2", "securityType2": "Common Stock", "securityDescription": "NCLH"}
        axta = {"figi": "BBG0060CPLJ5", "name": "AXALTA COATING SYSTEMS LTD", "ticker": "AXTA", "exchCode": "US",
                "compositeFIGI": "BBG0060CPLJ5", "securityType": "Common Stock", "marketSector": "Equity",
                "shareClassFIGI": "BBG0060CPLK3", "securityType2": "Common Stock", "securityDescription": "AXTA"}
        # 허벌라이프는 아직 원본을 못 봤다 — 옛 규칙이 'COM SHS' 에서 묻지도 않았다.
        # 그래서 여기서는 종류 칸이 통과하는지만 본다(이름은 가장 흔한 모양).
        hlf = {**axta, "name": "HERBALIFE LTD", "ticker": "HLF", "shareClassFIGI": "H"}
        for cusip, name, cls, ticker, row in (("G66721104", "NORWEGIAN CRUISE LINE HLDGS", "SHS", "NCLH", ncl),
                                              ("G0750C108", "AXALTA COATING SYS LTD", "COM", "AXTA", axta),
                                              ("G4412G101", "HERBALIFE LTD", "COM SHS", "HLF", hlf)):
            with self.subTest(ticker=ticker):
                required = {cusip: {"name": name, "class": cls}}
                later = set()
                with patch.object(p, "request", side_effect=[[{}], [{"data": [row]}]]):
                    self.assertEqual(p.resolve([cusip], required, {cusip: ticker}, later), {cusip: ticker})
                self.assertEqual(later, {cusip})

    def test_loose_name_rules_still_refuse_other_companies(self):
        self.assertFalse(p.same_issuer("NORWEGIAN AIR SHUTTLE ASA", "NORWEGIAN CRUISE LINE HLDGS"))
        self.assertFalse(p.same_issuer("AXALTA COATING SYSTEMS LTD", "AXON ENTERPRISE INC"))
        # 짧은 앞부분(2글자 이하)은 줄임말로 안 받는다.
        self.assertFalse(p.same_issuer("AB INDUSTRIES", "ABC INDUSTRIES"))
        # 28글자 미만이면 잘린 것이 아니다 — 끝 낱말이 달라도 봐주지 않는다.
        self.assertFalse(p.same_issuer("NORWEGIAN CRUISE LINE X", "NORWEGIAN CRUISE LINE HLDGS"))
        # 종류가 적힌 줄(CL A 등)은 로고용 옛 티커로 붙이지 않는다 — 에이온·리버티 C주.
        for cls in ("SHS CL A", "COM CL C"):
            req = {"G0403H108": {"name": "AON PLC", "class": cls}}
            with patch.object(p, "request", return_value=[{}]), patch("builtins.print"):
                self.assertEqual(p.resolve(list(req), req, {"G0403H108": "AON"}), {})

    def test_class_letter_lines_pick_the_matching_class_from_a_name_search(self):
        def share(name, ticker):
            return {"name": name, "ticker": ticker, "exchCode": "US", "securityType": "Common Stock",
                    "marketSector": "Equity", "shareClassFIGI": ticker}
        liberty = {"data": [share("LIBERTY GLOBAL LTD-A", "LBTYA"), share("LIBERTY GLOBAL LTD-B", "LBTYB"),
                            share("LIBERTY GLOBAL LTD-C", "LBTYK"),
                            share("LIBERTY LATIN AMERICA LTD-C", "LILAK"),
                            {**share("LIBERTY GLOBAL LTD-C", "LBTYK"), "exchCode": "LN"}]}
        req = {"G61188127": {"name": "LIBERTY GLOBAL LTD", "class": "COM CL C"}}
        later = set()
        with patch.object(p, "request", side_effect=[[{}], liberty]):
            # 로고 표에 적힌 LBTYA(A주)가 아니라 C주를 고른다.
            self.assertEqual(p.resolve(list(req), req, {"G61188127": "LBTYA"}, later), {"G61188127": "LBTYK"})
        self.assertEqual(later, {"G61188127"})
        # 같은 글자가 둘이거나(모호) 없으면 안 붙인다.
        twice = {"data": liberty["data"] + [share("LIBERTY GLOBAL LTD-C", "LBTYC")]}
        for found in (twice, {"data": liberty["data"][:2]}, {"data": []}):
            with patch.object(p, "request", side_effect=[[{}], found]), patch("builtins.print"):
                self.assertEqual(p.resolve(list(req), req, {}), {})
        # 종류 꼬리 없는 이름: 그 회사 미국 보통주가 하나뿐이고 공시가 A주일 때만.
        aon = {"G0403H108": {"name": "AON PLC", "class": "SHS CL A"}}
        with patch.object(p, "request", side_effect=[[{}], {"data": [share("AON PLC", "AON")]}]):
            self.assertEqual(p.resolve(list(aon), aon, {}), {"G0403H108": "AON"})
        aon_c = {"G0403H108": {"name": "AON PLC", "class": "SHS CL C"}}
        with patch.object(p, "request", side_effect=[[{}], {"data": [share("AON PLC", "AON")]}]), patch("builtins.print"):
            self.assertEqual(p.resolve(list(aon_c), aon_c, {}), {})
        # 이름 검색이 통신 장애면 조용히 넘어가지 않는다(짝 없음이 아니라 고장).
        with patch.object(p, "request", side_effect=[[{}], ValueError("offline")]):
            with self.assertRaises(ValueError):
                p.resolve(list(aon), aon, {})

    def test_a_failed_class_search_is_an_outage_for_that_line_only(self):
        required = {"G0403H108": {"name": "AON PLC", "class": "SHS CL A"},
                    "G66721104": {"name": "NORWEGIAN CRUISE LINE HLDGS", "class": "SHS"}}
        ncl = {"name": "NORWEGIAN CRUISE LINE HOLDIN", "ticker": "NCLH", "exchCode": "US",
               "securityType": "Common Stock", "marketSector": "Equity", "shareClassFIGI": "N"}
        now = dt.datetime(2026, 9, 18, 1, tzinfo=p.UTC)
        with patch.object(p, "request", side_effect=[[{}, {}], [{"data": [ncl]}], ValueError("429"),
                                                     chart(symbol="NCLH")]), \
                patch.object(p.time, "sleep"), patch("builtins.print"):
            result, errors = p.collect(required, {}, now, known={"G66721104": "NCLH"},
                                       quarter_marks={"G66721104": ("2026-09-17", 101)})
        # 노르웨이지언은 그대로 붙고, 에이온은 '짝 없음'이 아니라 고장(빨간불)으로 남는다.
        self.assertEqual(result["series"]["G66721104"]["ticker"], "NCLH")
        self.assertEqual((len(errors), result.get("unpriced")), (1, None))

    def test_quarter_end_mark_undoes_later_splits(self):
        self.assertTrue(p.mark_matches([("2026-06-29", 49), ("2026-06-30", 50)], {"2026-08-01": "2:1"}, ("2026-06-30", 100)))
        self.assertFalse(p.mark_matches([("2026-06-30", 50)], {}, ("2026-06-30", 100)))
        self.assertFalse(p.mark_matches([("2026-06-30", 102.1)], {}, ("2026-06-30", 100)))
        self.assertTrue(p.mark_matches([("2026-06-30", 101.9)], {}, ("2026-06-30", 100)))
        # 러너가 찍은 토름 숫자 그대로 — 코펜하겐 종가를 달러로 바꾼 공시 (+1.06%)
        self.assertTrue(p.mark_matches([("2026-06-30", 26.06)], {}, ("2026-06-30", 25.7877)))
        # 분기말 앞뒤로 종가가 없으면 잴 수 없다 — 못 잰 것은 맞지 않은 것이다.
        self.assertFalse(p.mark_matches([("2026-09-17", 100)], {}, ("2026-06-30", 100)))
        self.assertFalse(p.mark_matches([("2026-06-30", 100)], {}, ("", 0)))

    def run_torm(self, mark):
        required = {"G89479102": {"name": "TORM PLC", "class": "COMMON STOCK"}}
        with patch.object(p, "request", side_effect=[[{}], [{"data": [TORM]}], chart(symbol="TRMD")]), \
                patch.object(p.time, "sleep"):
            return p.collect(required, {}, dt.datetime(2026, 9, 19, 1, tzinfo=p.UTC),
                             known={"G89479102": "TRMD"}, quarter_marks={"G89479102": mark})

    def test_a_name_matched_ticker_is_kept_only_when_its_close_matches_the_filing(self):
        result, errors = self.run_torm(("2026-09-17", 101))
        self.assertEqual((errors, result["series"]["G89479102"]["ticker"]), ([], "TRMD"))
        self.assertNotIn("unpriced", result)
        result, errors = self.run_torm(("2026-09-17", 95))
        self.assertEqual((errors, result["series"]), ([], {}))
        # 얼마나 어긋났는지를 숫자로 남긴다 — 이유 없이 '안 맞음'만 있으면 판단을 못 한다.
        self.assertIn("close 101.0000 on 2026-09-17 vs filing 95.0000 for 2026-09-17 (+6.32%)",
                      result["unpriced"]["G89479102"]["reason"])

    def test_no_match_is_a_known_state_but_an_outage_is_not(self):
        required = {"81761L102": {"name": "SERVICE PROPERTIES TRUST", "class": "COMMON STOCK"}}
        now = dt.datetime(2026, 9, 19, 1, tzinfo=p.UTC)
        with patch.object(p, "request", return_value=[{"warning": "No identifier found."}]), patch.object(p.time, "sleep"):
            result, errors = p.collect(required, {}, now)
        self.assertEqual((errors, list(result["unpriced"])), ([], ["81761L102"]))
        with patch.object(p, "request", side_effect=ValueError("offline")), patch.object(p.time, "sleep"):
            result, errors = p.collect(required, {}, now)
        self.assertEqual((len(errors), result.get("unpriced")), (2, None))

    def test_price_source_404_is_known_only_for_a_ticker_never_priced(self):
        gone = p.urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        required = {"8676EP108": {"name": "SUNOPTA INC", "class": "COMMON STOCK"}}
        now = dt.datetime(2026, 9, 19, 1, tzinfo=p.UTC)
        mapping = [{"data": [{"ticker": "STKL", "marketSector": "Equity", "exchCode": "US"}]}]
        with patch.object(p, "request", side_effect=[mapping, gone]) as req, patch.object(p.time, "sleep"):
            result, errors = p.collect(required, {}, now)
        self.assertEqual((errors, list(result["unpriced"])), ([], ["8676EP108"]))
        old = {"series": {"8676EP108": {"ticker": "STKL", "values": [["2026-09-17", 1]], "splits": {}}}}
        # 평일(금) — 이미 티커가 있으니 짝을 다시 묻지 않고 종가만 받는다.
        with patch.object(p, "request", side_effect=gone), patch.object(p.time, "sleep"):
            result, errors = p.collect(required, old, dt.datetime(2026, 9, 18, 1, tzinfo=p.UTC))
        self.assertEqual((len(errors), result.get("unpriced")), (1, None))
        self.assertEqual(result["series"], old["series"])

    def test_a_new_unpriced_holding_turns_the_run_red_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, folder = Path(tmp)/"prices.json", Path(tmp)/"prices"
            book = {"quarters": [{"period": "2026-06-30", "holdings": [
                {"cusip": "123456100", "name": "A", "shares": 1, "value": 1}]}]}
            inv = type("Inv", (), {"slug": "x", "output": out})()
            got = ({"method": "split-adjusted-close", "series": {},
                    "unpriced": {"123456100": {"ticker": "", "reason": "exact CUSIP mapping unavailable"}}}, [])
            def run():
                with patch.object(p.registry, "load", return_value=[inv]), \
                        patch.object(p, "books", return_value=[book]), patch.object(p, "OUT", out), \
                        patch.object(p, "PER", folder), patch.object(p, "collect", return_value=got), \
                        patch.object(p.sys, "argv", ["fetch_prices.py"]), patch("builtins.print"):
                    p.main()
            with self.assertRaises(SystemExit):
                run()
            self.assertIn("123456100", json.loads(out.read_text())["unpriced"])
            run()   # 다음 날: 같은 종목이면 초록불
