"""Daily adjusted data export: no network, no notifications."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import samuel_data as data
import fetch_long as history


def fixture(n=1300):
    points = {}
    day = date(2010, 1, 4)
    while len(points) < n:
        if day.weekday() < 5:
            points[day.isoformat()] = 100 + len(points) / 100
        day += timedelta(days=1)
    return {key: points.copy() for key in data.SYMBOLS}

AS_OF = date.fromisoformat(max(fixture()["spx"])) + timedelta(days=1)

def publish(quotes, output, today=AS_OF):
    return data.publish(quotes, output, today)

class Export(unittest.TestCase):
    def test_all_daily_rows_remain_and_identical_export_does_not_change_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prices.json"
            quotes = fixture()
            self.assertTrue(publish(quotes, path))
            packed = json.loads(path.read_text())
            self.assertEqual(packed["basis"], "dividend-adjusted")
            self.assertEqual(packed["frequency"], "daily")
            self.assertEqual(len(packed["series"]["spx"]["series"]), 1300)
            old = path.read_bytes()
            self.assertFalse(publish(quotes, path))
            self.assertEqual(path.read_bytes(), old)

    def test_missing_asset_shrinking_history_and_invalid_values_preserve_previous_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prices.json"
            quotes = fixture()
            publish(quotes, path)
            old = path.read_bytes()
            bad = fixture(); bad["spx"][next(iter(bad["spx"]))] = float("nan")
            missing_day = fixture(); missing_day["spx"].pop(next(iter(missing_day["spx"])))
            missing_middle = fixture(); missing_middle["spx"].pop(sorted(missing_middle["spx"])[500])
            for candidate in ({"spx": quotes["spx"]}, fixture(1000), bad, missing_day, missing_middle):
                with self.assertRaises(ValueError):
                    publish(candidate, path)
                self.assertEqual(path.read_bytes(), old)

    def test_current_session_is_excluded_and_large_gap_is_rejected(self):
        quotes = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prices.json"
            end = max(quotes["spx"])
            publish(quotes, path, date.fromisoformat(end))
            self.assertLess(json.loads(path.read_text())["series"]["spx"]["to"], end)
            holed = fixture()
            days = sorted(holed["spx"])
            for day in days[100:120]:
                del holed["spx"][day]
            with self.assertRaisesRegex(ValueError, "gap"):
                publish(holed, path)

    def test_stale_response_preserves_last_complete_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prices.json"
            quotes = fixture()
            publish(quotes, path)
            old = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "stale"):
                publish(quotes, path, AS_OF+timedelta(days=10))
            self.assertEqual(path.read_bytes(), old)

    def test_etfs_never_fall_back_to_unadjusted_prices(self):
        raw = json.dumps({"chart": {"result": [{"indicators": {"quote": [{"close": [100]}]}, "timestamp": [1]}]}}).encode()
        for symbol in ("SPY", "QQQ", "BIL"):
            with patch.object(history, "fetch", return_value=raw), self.assertRaisesRegex(RuntimeError, "배당 반영"):
                history.yahoo_daily(symbol)

    def test_weekly_job_reuses_full_points_before_thinning_and_reports_export_failure(self):
        quotes = fixture()
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(history, "OUT", str(Path(temporary) / "market-long.json")), \
             patch.object(history, "yahoo_daily", side_effect=[quotes["spx"], quotes["ndx"], quotes["spx"], quotes["reserve"]]), \
             patch.object(history, "load_fng", return_value=quotes["spx"]), \
             patch.object(history, "publish_samuel", side_effect=ValueError("export down")) as publish, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(history.main(), 1)
            self.assertEqual(publish.call_args.args[0], quotes)
            self.assertTrue((Path(temporary) / "market-long.json").exists())

    def test_bil_gap_cannot_be_filled_with_zero_interest_or_a_carried_price(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prices.json"
            quotes = fixture()
            quotes["reserve"].pop(sorted(quotes["reserve"])[500])
            with self.assertRaisesRegex(ValueError, "BIL session"):
                publish(quotes, path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
