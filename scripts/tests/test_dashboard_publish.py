import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publish_dashboard import DATA, FILES, project, publish


class DashboardPublishTests(unittest.TestCase):
    def test_projection_preserves_every_non_vix_value_and_source(self):
        for name in FILES:
            with self.subTest(name=name):
                source = json.loads((DATA / name).read_text(encoding="utf-8"))
                original = copy.deepcopy(source)
                result = project(name, source)
                self.assertEqual(source, original)
                # Adding back only VIX reconstructs the entire original, including dates.
                if name == "market.json":
                    self.assertNotIn("vix", result)
                    result["vix"] = source["vix"]
                elif name == "market-long.json":
                    self.assertNotIn("vix", result["series"])
                    result["series"]["vix"] = source["series"]["vix"]
                else:
                    self.assertEqual([a["key"] for a in result["axes"]], ["fng"])
                    result["axes"] = source["axes"]
                    for key, index in result["indices"].items():
                        self.assertNotIn("vix", index["curve"])
                        index["curve"]["vix"] = source["indices"][key]["curve"]["vix"]
                self.assertEqual(result, source)

    def test_committed_visitor_files_match_sources(self):
        for name in FILES:
            source = json.loads((DATA / name).read_text(encoding="utf-8"))
            visitor = json.loads((DATA / "dashboard" / name).read_text(encoding="utf-8"))
            self.assertEqual(visitor, project(name, source), name)

    def test_partial_source_keeps_timestamp_and_other_target_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            source = {"updated": None, "indices": {"spx": {"value": 100}}, "fng": {}, "vix": {"value": 15}}
            (data / "market.json").write_text(json.dumps(source), encoding="utf-8")
            publish("market.json", data)
            target = data / "dashboard" / "market.json"
            first = target.read_bytes()
            publish("market.json", data)
            self.assertEqual(target.read_bytes(), first)
            self.assertEqual(json.loads(first), {k: v for k, v in source.items() if k != "vix"})
            self.assertEqual([p.name for p in target.parent.iterdir()], ["market.json"])

    def test_unreadable_source_does_not_replace_last_visitor_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "dashboard").mkdir()
            target = data / "dashboard" / "market.json"
            target.write_text('{"updated":"old"}', encoding="utf-8")
            (data / "market.json").write_text('{broken', encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                publish("market.json", data)
            self.assertEqual(target.read_text(encoding="utf-8"), '{"updated":"old"}')
