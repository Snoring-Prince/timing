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


# 흉내 공시 한 건. 항목 이름은 `test_amendments.py` 와 같은 실물 모양입니다.
_NS = 'http://www.sec.gov/edgar/thirteenffiler'
_TNS = 'http://www.sec.gov/edgar/document/thirteenf/informationtable'
TABLE = (f'<?xml version="1.0"?><informationTable xmlns="{_TNS}">'
         '<infoTable><nameOfIssuer>ALPHA CORP</nameOfIssuer>'
         '<titleOfClass>COM</titleOfClass><cusip>111111111</cusip>'
         '<value>20000</value><shrsOrPrnAmt><sshPrnamt>100</sshPrnamt>'
         '<sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>'
         '</informationTable>').encode()
COVER = (f'<?xml version="1.0"?><edgarSubmission xmlns="{_NS}"><formData>'
         '<coverPage><reportCalendarOrQuarter>09-30-2026</reportCalendarOrQuarter>'
         '</coverPage><summaryPage><tableValueTotal>20000</tableValueTotal>'
         '<tableEntryTotal>1</tableEntryTotal></summaryPage>'
         '</formData></edgarSubmission>').encode()


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
        # **종료코드 1 이 맞습니다.** 이 검사는 원문 받기를 막아 두므로(run_fetch
        # 기본값) 정정을 합칠 수 없고, 합치지 못한 분기는 원본 숫자로 남습니다.
        # 예전에는 그래도 0 이라 워크플로가 초록불이었습니다 — 자료는 저장하되
        # 빨간불로 끝내는 것이 이번에 고친 자리입니다.
        amend = {**self.latest(), 'accession': 'fixture-amendment'}
        self.assertEqual(self.run_fetch([self.latest()], [amend]), 1)
        after = json.loads(self.out.read_text())
        self.assertEqual(len(after['quarters']), len(self.book['quarters']))
        self.assertIn('fixture-amendment', after['quarters'][-1]['amended_by'])
        self.assertNotEqual(after['updated'], self.book['updated'])
        self.assertTrue(self.alert.exists())
        self.alert.unlink()
        saved = self.out.read_bytes()
        # 두 번째 실행도 여전히 못 합치므로 빨간불입니다. 다만 **쪽지는 한 번만**
        # 갑니다 — 이미 아는 정정이라 새로 뜬 것이 아닙니다.
        self.assertEqual(self.run_fetch([self.latest()], [amend]), 1)
        self.assertEqual(self.out.read_bytes(), saved)
        self.assertFalse(self.alert.exists())

    def test_one_good_quarter_does_not_make_a_failed_one_green(self):
        """**한 분기라도 성공하면 초록불**이던 것을 고쳤습니다.

        예전 조건은 `failed and not got` 이라, 새 분기 하나가 성공하고 다른
        하나가 실패하면 종료코드 0 이었습니다. 빠진 분기가 있는 JSON 이 조용히
        커밋되고, 화면은 두 분기치 증감을 `이번 분기` 라고 적습니다."""
        good = {'period': '2026-09-30', 'filed': '2026-11-14',
                'accession': 'fixture-good'}
        bad = {'period': '2026-12-31', 'filed': '2027-02-13',
               'accession': 'fixture-bad'}
        docs = {'fixture-good': (TABLE, COVER), 'fixture-bad': (None, None)}
        with patch.dict(os.environ, {'SEC_CONTACT': 'fixture-only'}), \
                patch.object(fetch, 'OUT', str(self.out)), \
                patch.object(fetch, 'ALERT', str(self.alert)), \
                patch.object(fetch, 'filing_docs',
                             side_effect=lambda acc, _c: docs.get(acc, (None, None))), \
                patch.object(fetch, 'list_filings',
                             return_value=([self.latest(), good, bad], [])), \
                contextlib.redirect_stdout(io.StringIO()):
            code = fetch.main()
        after = json.loads(self.out.read_text())
        got = [q['period'] for q in after['quarters']]
        # 성공한 분기는 **저장됩니다** — 실패했다고 받은 것까지 버리지 않습니다.
        self.assertIn('2026-09-30', got, '성공한 분기가 저장되지 않았습니다')
        self.assertNotIn('2026-12-31', got)
        # 그런데 자료에 구멍이 났으므로 **빨간불로 끝나야** 합니다.
        self.assertEqual(code, 1, '반쪽짜리 실행이 초록불로 끝났습니다')

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
