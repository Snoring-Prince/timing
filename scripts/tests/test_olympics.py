"""Public-date disclosures and adjusted prices; offline, no notifications."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from olympics.filings import collect, timeline, candidates, shares
from olympics.prices import parse, preserve
from olympics.identities import baseline_aliases
import fetch_olympics as export

def holding(cusip="A", n=10):
    return {"cusip": cusip, "name": "Example", "class": "COM", "shares": n, "value": n*10}
def disclosure(kind="ORIGINAL", filed="2025-02-14", period="2024-12-31", holdings=None, acc="orig"):
    return {"accession": acc, "kind": kind, "filed": filed, "period": period,
            "holdings": holdings or [holding()]}
def payload():
    return {"chart": {"result": [{"meta": {"symbol": "AAA", "currency": "USD"},
             "timestamp": [1735830000, 1735916400], "indicators": {"adjclose": [{"adjclose": [10, 11]}]},
             "events": {"splits": {"a": {"date": 1735916400, "numerator": 2, "denominator": 1}}}}]}}

class Disclosures(unittest.TestCase):
    def test_unamended_original_and_cached_disclosures_need_no_network(self):
        q={"period": "2024-12-31", "filed": "2025-02-14", "accession": "orig", "holdings": [holding()]}
        reader=Mock(side_effect=AssertionError("network"))
        got=collect({"quarters": [q]}, [], reader, reader)
        self.assertEqual(got, [disclosure()])
        self.assertEqual(collect({"quarters": [q]}, got, reader, reader), got)
    def test_amended_book_is_not_mistaken_for_the_original(self):
        q={"period": "2024-12-31", "filed": "2025-02-14", "accession": "orig", "amended_by": ["amend"], "holdings": [holding("B")]}
        reader=Mock(side_effect=[([holding()], None), ([holding("B")], "NEW HOLDINGS")])
        got=collect({"quarters": [q]}, [], reader, lambda: [{"accession": "amend", "filed": "2025-05-15"}])
        self.assertEqual([h["cusip"] for h in got[0]["holdings"]], ["A"])
        self.assertEqual(got[1]["filed"], "2025-05-15")
    def test_unknown_amendment_date_or_kind_preserves_input_cache(self):
        q={"period": "2024-12-31", "filed": "2025-02-14", "accession": "orig", "amended_by": ["amend"], "holdings": [holding()]}
        saved=[disclosure()]; before=json.dumps(saved)
        with self.assertRaisesRegex(ValueError, "public filing date"):
            collect({"quarters": [q]}, saved, Mock(), lambda: [])
        self.assertEqual(json.dumps(saved), before)
        with self.assertRaisesRegex(ValueError, "unknown"):
            collect({"quarters": [q]}, saved, lambda *a: ([holding("B")], "UNKNOWN"),
                    lambda: [{"accession": "amend", "filed": "2025-05-15"}])
    def test_new_holdings_and_restatements_apply_on_public_dates_only(self):
        docs=[disclosure(), disclosure("NEW HOLDINGS", "2025-03-01", holdings=[holding("B")], acc="amend"),
              disclosure("RESTATEMENT", "2025-03-04", holdings=[holding("A", 7),holding("B")], acc="restate")]
        got=timeline(docs, {"A": "AAA", "B": "BBB"})
        self.assertEqual([[h["key"] for h in e["holdings"]] for e in got], [["AAA"],["AAA","BBB"],["AAA","BBB"]])
        self.assertEqual(got[1]["filed"], "2025-03-01")
        self.assertEqual(got[-1]["holdings"][0]["shares"], 7)
    def test_old_quarter_amendment_cannot_rewind_the_current_portfolio(self):
        docs=[disclosure(), disclosure(filed="2025-05-15", period="2025-03-31", holdings=[holding("C")], acc="next"),
              disclosure("NEW HOLDINGS","2025-06-01",holdings=[holding("B")],acc="old-amend")]
        got=timeline(docs,{"A":"AAA","B":"BBB","C":"CCC"})
        self.assertEqual(len(got), 2); self.assertEqual(got[-1]["period"], "2025-03-31")
    def test_one_to_one_retired_identifier_does_not_become_a_new_entry(self):
        old=holding("531229748");old["name"]="LIBERTY MEDIA CORP DEL";old["class"]="COM LBTY LIV S A"
        aliases=baseline_aliases({old["cusip"]:old});self.assertEqual(aliases, {"531229748":"LLYVA"})
        docs=[disclosure(holdings=[old]),disclosure(filed="2025-05-15",period="2025-03-31",holdings=[holding("530909100")],acc="next")]
        got=timeline(docs, {**aliases,"530909100":"LLYVA"});self.assertEqual(candidates(got),set())
        with self.assertRaisesRegex(ValueError,"identity changed"):baseline_aliases({"531229748":holding("531229748")})
    def test_duplicate_ticker_classes_fail_instead_of_merging_stock_prices(self):
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            timeline([disclosure(holdings=[holding("A"),holding("B")])],{"A":"AAA","B":"AAA"})
    def test_options_and_non_share_lines_do_not_create_equity_candidates(self):
        good=holding();put={**holding("B"),"putCall":"PUT"};prn={**holding("C"),"type":"PRN"}
        self.assertEqual(shares([good,put,prn]),[good])

class Prices(unittest.TestCase):
    def test_adjusted_usd_prices_and_genuine_split_ratio(self):
        got=parse(payload(),"AAA","2025-01-05")
        self.assertEqual(got["series"],[("2025-01-02",10),("2025-01-03",11)])
        self.assertEqual(got["splits"],{"2025-01-03":2})
    def test_current_day_is_never_published_as_a_finished_close(self):
        self.assertEqual(len(parse(payload(),"AAA","2025-01-03")["series"]),1)
    def test_currency_symbol_raw_only_and_invalid_adjusted_prices_fail(self):
        for key,value in [("currency","EUR"),("symbol","BBB")]:
            p=payload();p["chart"]["result"][0]["meta"][key]=value
            with self.assertRaises(ValueError):parse(p,"AAA","2025-01-05")
        for value in [0,-1,True,float("nan")]:
            p=payload();p["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"][0]=value
            with self.assertRaises(ValueError):parse(p,"AAA","2025-01-05")
        p=payload();p["chart"]["result"][0]["indicators"]={"quote":[{"close":[10,11]}]}
        with self.assertRaisesRegex(ValueError,"adjusted"):parse(p,"AAA","2025-01-05")
    def test_spinoff_ratio_is_not_used_as_a_stock_split(self):
        p=payload();p["chart"]["result"][0]["events"]["splits"]["a"]["numerator"]=1.0428
        self.assertEqual(parse(p,"AAA","2025-01-05")["splits"],{})
    def test_partial_history_does_not_replace_a_complete_cache(self):
        prior=parse(payload(),"AAA","2025-01-05")
        incoming={**prior,"series":prior["series"][:1]}
        with self.assertRaisesRegex(ValueError,"shrank"):preserve(prior,incoming)
        self.assertEqual(len(prior["series"]),2)
    def test_publication_is_idempotent_and_keeps_adjusted_basis(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);files={"race.json":{"basis":"dividend-adjusted"}}
            export.publish(folder,files); stamp=(folder/"race.json").stat().st_mtime_ns
            export.publish(folder,files);self.assertEqual((folder/"race.json").stat().st_mtime_ns,stamp)
    def test_workflow_only_saves_success_and_reports_failure_through_existing_notifier(self):
        source=(export.ROOT/".github/workflows/update-olympics.yml").read_text()
        self.assertIn("if: steps.collect.outcome == 'success'",source)
        self.assertIn("steps.collect.outcome == 'failure'",source)
        self.assertIn("if: failure()",source);self.assertIn("python scripts/notify.py --title",source)

if __name__=="__main__":unittest.main()
