"""Root dashboard regressions. No network or messages."""
import contextlib
import io
import json
import statistics
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backtest as bt
import fetch_data as daily
import fetch_long as history

def prices(n=1600):
    out = {}
    day = date(2015, 1, 1)
    while len(out) < n:
        if day.weekday() < 5:
            out[day.isoformat()] = 100 + len(out)
        day += timedelta(days=1)
    return out

class Horizons(unittest.TestCase):
    def test_missing_indicator_days_do_not_extend_any_holding_period(self):
        px = prices()
        days = sorted(px)
        gauge = {d: 50 for i, d in enumerate(days) if not 100 <= i < 191}
        actual, entries = bt.backtest(gauge, px, 5)
        self.assertEqual(entries, sorted(gauge))
        for key, sessions in bt.HORIZONS:
            returns = [(px[days[i + sessions]] / px[d] - 1) * 100
                       for i, d in enumerate(days[:-sessions]) if d in gauge]
            with self.subTest(horizon=key):
                self.assertEqual(actual[key]["n"][50], len(returns))
                self.assertEqual(actual[key]["med"][50], round(statistics.median(returns), 2))
                self.assertEqual(actual[key]["avg"][50], round(statistics.mean(returns), 2))
                self.assertEqual(actual[key]["win"][50], 100)

    def test_complete_calendar_declines_zero_wins_and_minimum_samples(self):
        px = prices()
        px = {d: 2000 - v for d, v in px.items()}
        result, _ = bt.backtest({d: 50 for d in px}, px, 5)
        for key, span in bt.HORIZONS:
            self.assertEqual(result[key]["n"][50], len(px) - span)
            self.assertEqual(result[key]["win"][50], 0)
            self.assertLess(result[key]["med"][50], 0)
            self.assertIsNone(result[key]["med"][0])

    def test_one_missing_csv_is_a_failure_not_a_shorter_history(self):
        csv = b"Date,Fear Greed\n2011-01-03,50\n"
        for module in (bt, history):
            with self.subTest(module=module.__name__), patch.object(module, "fetch", side_effect=[csv, OSError("down")]):
                with self.assertRaises(RuntimeError):
                    module.load_fng()

    def test_incomplete_backtest_keeps_last_good_file(self):
        px = prices()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "backtest.json"
            out.write_bytes(b"previous complete statistics")
            with patch.object(bt, "OUT", str(out)), patch.object(bt, "load_fng", return_value={x: 50 for x in px}), \
                 patch.object(bt, "yahoo_daily", side_effect=[{x: 15 for x in px}, px, OSError("QQQ down")]), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    bt.main()
            self.assertEqual(out.read_bytes(), b"previous complete statistics")

class Collectors(unittest.TestCase):
    def daily_file(self):
        return {"updated": "2026-09-20T00:00:00Z",
                "indices": {"spx": {"cur": 100}, "ndx": {"cur": 200}},
                "fng": {"value": 35, "series": [["2026-09-18", 35]]},
                "vix": {"value": 15}}
    def long_file(self):
        return {"updated": "2026-09-20T00:00:00Z",
                "series": {k: {"n": 1, "series": [["2026-09-18", 35]]} for k in ("spx","ndx","fng","vix")}}

    def test_all_daily_failures_preserve_bytes_and_fail(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"market.json";out.write_text(json.dumps(self.daily_file()))
            old=out.read_bytes()
            with patch.object(daily,"OUT",str(out)), patch.object(daily,"build_index",side_effect=OSError("down")), \
                 patch.object(daily,"build_vix",side_effect=OSError("down")), \
                 patch.object(daily,"src_fng_mirror",side_effect=OSError("down")), \
                 patch.object(daily,"src_fng_cnn",side_effect=OSError("down")), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    daily.main()
            self.assertEqual(out.read_bytes(),old)

    def test_daily_partial_success_is_saved_but_returns_failure(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"market.json";old=self.daily_file();out.write_text(json.dumps(old))
            with patch.object(daily,"OUT",str(out)), patch.object(daily,"build_index",side_effect=[{"cur":101},OSError("QQQ down")]), \
                 patch.object(daily,"build_fng",return_value={"value":36}), \
                 patch.object(daily,"build_vix",return_value={"value":16}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(daily.main(),1)
            actual=json.loads(out.read_text())
            self.assertEqual(actual["updated"],old["updated"])
            self.assertEqual(actual["indices"]["spx"]["cur"],101)
            self.assertEqual(actual["indices"]["ndx"],old["indices"]["ndx"])

    def test_all_long_failures_preserve_bytes_and_fail(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"market-long.json";out.write_text(json.dumps(self.long_file()))
            old=out.read_bytes()
            with patch.object(history,"OUT",str(out)), patch.object(history,"yahoo_daily",side_effect=OSError("down")), \
                 patch.object(history,"load_fng",side_effect=OSError("down")), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    history.main()
            self.assertEqual(out.read_bytes(),old)

    def test_long_partial_success_is_saved_but_returns_failure(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"market-long.json";old=self.long_file();out.write_text(json.dumps(old))
            with patch.object(history,"OUT",str(out)), \
                 patch.object(history,"yahoo_daily",side_effect=[{"2026-09-23":100},OSError("QQQ down"),{"2026-09-23":15}]), \
                 patch.object(history,"load_fng",return_value={"2026-09-23":36}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(history.main(),1)
            actual=json.loads(out.read_text())
            self.assertEqual(actual["series"]["ndx"],old["series"]["ndx"])
            self.assertEqual(actual["series"]["spx"]["series"],[["2026-09-23",100]])
            self.assertEqual(actual["updated"],old["updated"])

    def test_successful_daily_collection_returns_zero(self):
        with tempfile.TemporaryDirectory() as d, patch.object(daily,"OUT",str(Path(d)/"market.json")), \
             patch.object(daily,"build_index",return_value={"cur":100}), patch.object(daily,"build_fng",return_value={"value":35}), \
             patch.object(daily,"build_vix",return_value={"value":15}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(daily.main(),0)

    def test_successful_long_collection_returns_zero(self):
        with tempfile.TemporaryDirectory() as d, patch.object(history,"OUT",str(Path(d)/"market-long.json")), \
             patch.object(history,"yahoo_daily",return_value={"2026-09-23":100}), \
             patch.object(history,"load_fng",return_value={"2026-09-23":35}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(history.main(),0)

if __name__ == "__main__":
    unittest.main()
