"""13F 갱신 회귀 검사. SEC 요청·실제 데이터 쓰기 없이 실행합니다.

python -m unittest discover -s scripts/tests -p 'test_*.py'
"""
import contextlib
import calendar
import datetime as dt
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('fetch_13f', ROOT / 'scripts/fetch_13f.py')
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'berkshire.json'
        self.alert = Path(self.tmp.name) / 'alert.txt'
        self.book = json.loads((ROOT / 'data/titans/berkshire.json').read_text(encoding='utf8'))
        self.out.write_text(json.dumps(self.book), encoding='utf8')
        self.before = self.out.read_bytes()

    def run_fetch(self, filings, amendments=(), docs=(None, None)):
        # 정정 병합이 생기면서 원문을 받는 자리가 하나 늘었습니다. 이 파일은
        # **SEC 요청 없이 도는 것이 약속**이므로(맨 위 설명) 기본값으로 막습니다.
        # (None, None) 은 '받지 못함'이라 병합을 보류하고 분기를 그대로 둡니다 —
        # 기존 검사들이 기대하는 '아무것도 안 바뀜'이 그대로 유지됩니다.
        with patch.dict(os.environ, {'SEC_CONTACT': 'fixture-only'}), \
                patch.object(fetch, 'OUT', str(self.out)), \
                patch.object(fetch, 'ALERT', str(self.alert)), \
                patch.object(fetch, 'filing_docs', return_value=docs), \
                patch.object(fetch, 'list_filings', return_value=(filings, list(amendments))), \
                contextlib.redirect_stdout(io.StringIO()):
            return fetch.main()

    def latest(self):
        return {k: self.book['quarters'][-1][k] for k in ('period', 'filed', 'accession')}

    def test_missing_submission_response_has_two_results(self):
        with patch.object(fetch, 'get', return_value=None):
            self.assertEqual(fetch.list_filings('fixture'), ([], []))

    def test_missing_older_chunk_rejects_partial_list(self):
        sub = {'filings': {'recent': {}, 'files': [{'name': 'older.json'}]}}
        with patch.object(fetch, 'get', side_effect=[json.dumps(sub).encode(), None]):
            self.assertEqual(fetch.list_filings('fixture'), ([], []))

    def test_oversized_xml_is_a_failure_not_old_text_format(self):
        index = {"directory": {"item": [
            {"name": "primary_doc.xml", "size": "1000"},
            {"name": "information_table.xml", "size": str(fetch.MAX_BYTES + 1)},
        ]}}
        with patch.object(fetch, 'get', return_value=json.dumps(index).encode()):
            self.assertEqual(fetch.filing_docs('0001', 'fixture'), (None, None))

    def test_failed_list_preserves_bytes(self):
        self.assertEqual(self.run_fetch([]), 1)
        self.assertEqual(self.out.read_bytes(), self.before)

    def test_partial_list_never_deletes_saved_history_or_amendments(self):
        self.assertEqual(self.run_fetch([self.latest()]), 0)
        self.assertEqual(self.out.read_bytes(), self.before)

    def test_unchanged_content_preserves_timestamp_and_bytes(self):
        filings = [{k: q[k] for k in ('period', 'filed', 'accession')}
                   for q in self.book['quarters']]
        amends = [{'period': q['period'], 'accession': acc, 'filed': q['filed']}
                  for q in self.book['quarters'] for acc in q.get('amended_by', [])]
        self.assertEqual(self.run_fetch(filings, amends), 0)
        self.assertEqual(self.out.read_bytes(), self.before)
        self.assertFalse(self.alert.exists())

    def test_new_amendment_saves_once_and_alerts_once(self):
        amend = {**self.latest(), 'accession': 'fixture-amendment'}
        self.assertEqual(self.run_fetch([self.latest()], [amend]), 0)
        after = json.loads(self.out.read_text())
        self.assertEqual(len(after['quarters']), len(self.book['quarters']))
        self.assertIn('fixture-amendment', after['quarters'][-1]['amended_by'])
        self.assertNotEqual(after['updated'], self.book['updated'])
        self.assertTrue(self.alert.exists())
        self.alert.unlink()
        saved = self.out.read_bytes()
        self.assertEqual(self.run_fetch([self.latest()], [amend]), 0)
        self.assertEqual(self.out.read_bytes(), saved)
        self.assertFalse(self.alert.exists())

    def test_bad_existing_json_is_not_rebuilt_over(self):
        self.out.write_text('{broken', encoding='utf8')
        self.assertEqual(self.run_fetch([self.latest()]), 1)
        self.assertEqual(self.out.read_text(), '{broken')

    def test_book_from_another_manager_is_never_combined(self):
        wrong = {**self.book, 'manager': {**self.book['manager'], 'cik': '0000000001'}}
        self.out.write_text(json.dumps(wrong), encoding='utf8')
        before = self.out.read_bytes()
        self.assertEqual(self.run_fetch([self.latest()]), 1)
        self.assertEqual(self.out.read_bytes(), before)

    def test_new_quarter_is_added_without_dropping_history(self):
        last = dt.date.fromisoformat(self.latest()['period'])
        next_q = last.year * 4 + last.month // 3
        year, month = next_q // 4, (next_q % 4 + 1) * 3
        period = dt.date(year, month, calendar.monthrange(year, month)[1])
        new = {'period': period.isoformat(), 'filed': (period + dt.timedelta(days=45)).isoformat(),
               'accession': 'fixture-new'}
        rows = [{'cusip': '123456789', 'name': 'Fixture', 'class': 'COM',
                 'type': 'SH', 'putCall': '', 'shares': 100, 'value': 10000}]
        with patch.object(fetch, 'rows_of', return_value=rows):
            self.assertEqual(self.run_fetch([new], docs=(b'fixture', None)), 0)
        after = json.loads(self.out.read_text())
        self.assertEqual(len(after['quarters']), len(self.book['quarters']) + 1)
        self.assertEqual(after['quarters'][:-1], self.book['quarters'])
        self.assertEqual(after['quarters'][-1]['total'], 10000)

    def test_interrupted_write_leaves_existing_file_whole(self):
        amend = {**self.latest(), 'accession': 'fixture-amendment'}
        with patch.object(fetch.json, 'dump', side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError):
                self.run_fetch([self.latest()], [amend])
        self.assertEqual(self.out.read_bytes(), self.before)


if __name__ == '__main__':
    unittest.main()
