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
from types import SimpleNamespace
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


class PredecessorTests(unittest.TestCase):
    """테퍼처럼 법인 번호가 바뀐 투자자 — 예전 번호의 공시를 한 번에 이어 붙입니다."""

    NEW, OLD = '0001656456', '0001006438'

    def sub(self, rows):
        return json.dumps({'filings': {'recent': {
            'form': [r[0] for r in rows], 'reportDate': [r[1] for r in rows],
            'filingDate': [r[2] for r in rows], 'accessionNumber': [r[3] for r in rows]}}}).encode()

    def table(self, value):
        return TABLE.replace(b'<value>20000</value>', f'<value>{value}</value>'.encode())

    def test_old_number_fills_the_years_before_the_new_one_and_is_fetched_from_its_own_folder(self):
        subs = {
            self.NEW: self.sub([('13F-HR', '2016-03-31', '2016-05-13', '2222222222-16-000001'),
                                ('13F-HR', '2016-06-30', '2016-08-12', '2222222222-16-000002')]),
            # 겹치는 2016-03-31 은 새 법인의 것이 이긴다 — 예전 번호에서는 버린다.
            self.OLD: self.sub([('13F-HR', '2015-09-30', '2015-11-13', '1111111111-15-000001'),
                                ('13F-HR', '2015-12-31', '2016-02-12', '1111111111-16-000002'),
                                ('13F-HR', '2016-03-31', '2016-05-13', '1111111111-16-000009'),
                                ('13F-HR/A', '2015-12-31', '2016-03-01', '1111111111-16-000003')]),
        }
        asked = []

        def fake_get(url, contact):
            asked.append(url)
            for cik, body in subs.items():
                if url.endswith(f'CIK{cik}.json'):
                    return body
            if url.endswith('/index.json'):
                return json.dumps({'directory': {'item': [
                    {'name': 'primary_doc.xml', 'size': '100'},
                    {'name': 'table.xml', 'size': '100'}]}}).encode()
            if url.endswith('/table.xml'):
                return self.table(20)          # 2023년 전 → 천 달러 단위
            if url.endswith('/primary_doc.xml'):
                cover = COVER.replace(b'20000', b'20')
                if '/111111111116000003/' in url:
                    cover = cover.replace(b'<coverPage>', b'<coverPage><amendmentInfo>'
                                          b'<amendmentType>NEW HOLDINGS</amendmentType>'
                                          b'</amendmentInfo>')
                return cover
            return None

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'appaloosa.json'
            inv = SimpleNamespace(slug='appaloosa', cik=self.NEW, filing_name='Appaloosa LP',
                                  output=out, since=2013, name={'ko': '애팔루사', 'en': 'Appaloosa'},
                                  predecessors=((self.OLD, 'Appaloosa Management LP'),))
            with patch.dict(os.environ, {'SEC_CONTACT': 'fixture-only'}), \
                    patch.object(fetch, 'one', return_value=inv), \
                    patch.object(fetch, 'ALERT', str(Path(tmp) / 'alert.txt')), \
                    patch.object(fetch, 'get', side_effect=fake_get), \
                    patch.object(fetch, 'ACC_CIK', {}), \
                    patch.multiple(fetch, CIK=fetch.CIK, OUT=fetch.OUT, MANAGER_NAME=fetch.MANAGER_NAME,
                                   PREDECESSORS=fetch.PREDECESSORS), \
                    contextlib.redirect_stdout(io.StringIO()):
                # main 이 전역 설정을 이 투자자로 바꾸므로 끝나면 되돌린다(다른 검사가 버크셔로 돈다).
                self.assertEqual(fetch.main('appaloosa'), 0)
            book = json.loads(out.read_text(encoding='utf8'))
        qs = book['quarters']
        self.assertEqual([q['period'] for q in qs], ['2015-09-30', '2015-12-31', '2016-03-31', '2016-06-30'])
        self.assertEqual([q.get('filer_cik') for q in qs], [self.OLD, self.OLD, None, None])
        self.assertEqual(qs[2]['accession'], '2222222222-16-000001')
        self.assertEqual(qs[1]['amended_by'], ['1111111111-16-000003'])
        # 책은 지금 번호의 것이고, 예전 번호를 밝혀 둔다.
        self.assertEqual(book['manager'], {'cik': self.NEW, 'name': 'Appaloosa LP',
                                           'predecessors': [self.OLD]})
        # 원문은 낸 법인의 폴더에서 받는다(다른 번호로 물으면 SEC 가 못 찾는다).
        self.assertTrue(any(f'/data/{int(self.OLD)}/111111111115000001/' in u for u in asked))
        self.assertTrue(any(f'/data/{int(self.NEW)}/222222222216000001/' in u for u in asked))
        self.assertFalse(any('111111111116000009' in u for u in asked))
        # 예전 번호의 정정도 그 법인 폴더에서 받아 합친다.
        self.assertTrue(any(f'/data/{int(self.OLD)}/111111111116000003/' in u for u in asked))
        self.assertEqual([a['accession'] for a in qs[1]['amended_applied']], ['1111111111-16-000003'])


class MergeOverlapTests(unittest.TestCase):
    """애크먼처럼 두 법인이 **같은 분기**를 각자 낸 경우 — 겹친 분기는 합칩니다.

    지금 번호(지주회사)가 2025-06-30 부터 자기 몫 하워드 휴즈만 따로 냈고, 펀드 몫은
    예전 번호가 냈습니다. 정찰 6차 실측 18,852,064 + 9,000,000 = 27,852,064 를
    그대로 씁니다."""

    NEW, OLD = '0002026053', '0001336528'
    HHH, ALPHA, BETA, GAMMA = '44267T102', '111111111', '222222222', '333333333'

    def sub(self, rows):
        return json.dumps({'filings': {'recent': {
            'form': [r[0] for r in rows], 'reportDate': [r[1] for r in rows],
            'filingDate': [r[2] for r in rows], 'accessionNumber': [r[3] for r in rows]}}}).encode()

    def table(self, rows):
        body = ''.join(
            f'<infoTable><nameOfIssuer>{n}</nameOfIssuer><titleOfClass>COM</titleOfClass>'
            f'<cusip>{c}</cusip><value>{v}</value><shrsOrPrnAmt><sshPrnamt>{s}</sshPrnamt>'
            '<sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>' for n, c, s, v in rows)
        return f'<?xml version="1.0"?><informationTable xmlns="{_TNS}">{body}</informationTable>'.encode()

    def cover(self, rows, amend=''):
        info = (f'<amendmentInfo><amendmentType>{amend}</amendmentType></amendmentInfo>'
                if amend else '')
        return (f'<?xml version="1.0"?><edgarSubmission xmlns="{_NS}"><formData>'
                f'<coverPage>{info}</coverPage><summaryPage>'
                f'<tableValueTotal>{sum(r[3] for r in rows)}</tableValueTotal>'
                f'<tableEntryTotal>{len(rows)}</tableEntryTotal></summaryPage>'
                '</formData></edgarSubmission>').encode()

    def run_merge(self, merge=True, docs_patch=None, hide=(), where=None):
        hh = ('HOWARD HUGHES HOLDINGS INC', self.HHH)
        docs = {
            # 예전 번호(펀드)
            '111111111125000001': [('ALPHA CORP', self.ALPHA, 100, 5000), (*hh, 18852064, 1_300_000_000)],
            '111111111125000002': [('ALPHA CORP', self.ALPHA, 100, 6000), (*hh, 18852064, 1_400_000_000),
                                   ('BETA CORP', self.BETA, 500, 1000)],
            '111111111125000003': [('GAMMA CORP', self.GAMMA, 10, 100)],            # 예전 번호의 정정
            # 지금 번호(지주회사) — 2025-06-30 은 하워드 휴즈 + 두 법인이 똑같이 적은 BETA
            '222222222225000001': [(*hh, 9000000, 600_000_000), ('BETA CORP', self.BETA, 500, 1000)],
            '222222222225000002': [('ALPHA CORP', self.ALPHA, 100, 7000), (*hh, 27852064, 2_000_000_000)],
        }
        amend = {'111111111125000003': 'NEW HOLDINGS'}
        subs = {
            self.NEW: self.sub([('13F-HR', '2025-06-30', '2025-08-14', '2222222222-25-000001'),
                                ('13F-HR', '2025-09-30', '2025-11-14', '2222222222-25-000002')]),
            self.OLD: self.sub([('13F-HR', '2025-03-31', '2025-05-15', '1111111111-25-000001'),
                                ('13F-HR', '2025-06-30', '2025-08-14', '1111111111-25-000002'),
                                ('13F-HR/A', '2025-06-30', '2025-09-01', '1111111111-25-000003')]),
        }
        if hide:
            # 아직 안 나온 공시 — 목록에서 뺍니다(늦게 도착하는 경우를 흉내 냅니다).
            subs = {cik: json.dumps({'filings': {'recent': {k: [v for v, a in zip(
                        vals, raw['filings']['recent']['accessionNumber']) if a not in hide]
                        for k, vals in raw['filings']['recent'].items()}}}).encode()
                    for cik, raw in ((c, json.loads(b)) for c, b in subs.items())}
        asked = []

        def fake_get(url, contact):
            asked.append(url)
            for cik, body in subs.items():
                if url.endswith(f'CIK{cik}.json'):
                    return body
            acc = url.rstrip('/').split('/')[-2]
            if docs_patch and acc in docs_patch:
                return None
            if url.endswith('/index.json'):
                return json.dumps({'directory': {'item': [
                    {'name': 'primary_doc.xml', 'size': '100'},
                    {'name': 'table.xml', 'size': '100'}]}}).encode()
            if url.endswith('/table.xml'):
                return self.table(docs[acc])
            if url.endswith('/primary_doc.xml'):
                return self.cover(docs[acc], amend.get(acc, ''))
            return None

        with (contextlib.nullcontext(where) if where else tempfile.TemporaryDirectory()) as tmp:
            out = Path(tmp) / 'pershing.json'
            inv = SimpleNamespace(slug='pershing', cik=self.NEW, filing_name='Pershing Square Inc.',
                                  output=out, since=2013, name={'ko': '퍼싱 스퀘어', 'en': 'Pershing Square'},
                                  predecessors=((self.OLD, 'Pershing Square Capital Management, L.P.'),),
                                  merge_overlap=(self.OLD,) if merge else ())
            with patch.dict(os.environ, {'SEC_CONTACT': 'fixture-only'}), \
                    patch.object(fetch, 'one', return_value=inv), \
                    patch.object(fetch, 'ALERT', str(Path(tmp) / 'alert.txt')), \
                    patch.object(fetch, 'get', side_effect=fake_get), \
                    patch.object(fetch, 'ACC_CIK', {}), \
                    patch.multiple(fetch, CIK=fetch.CIK, OUT=fetch.OUT, MANAGER_NAME=fetch.MANAGER_NAME,
                                   PREDECESSORS=fetch.PREDECESSORS, MERGE=fetch.MERGE), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = fetch.main('pershing')
            book = json.loads(out.read_text(encoding='utf8'))
        return code, book, asked

    def test_overlapping_quarter_adds_both_pockets_and_counts_a_double_report_once(self):
        code, book, asked = self.run_merge()
        self.assertEqual(code, 0)
        qs = {q['period']: q for q in book['quarters']}
        self.assertEqual(list(qs), ['2025-03-31', '2025-06-30', '2025-09-30'])
        self.assertEqual(qs['2025-03-31'].get('filer_cik'), self.OLD)
        q = qs['2025-06-30']
        self.assertEqual(q['accession'], '2222222222-25-000001')
        self.assertEqual([p['accession'] for p in q['partners']], ['1111111111-25-000002'])
        held = {h['cusip']: h for h in q['holdings']}
        # 두 주머니를 더한 하워드 휴즈 = 합쳐 낸 다음 분기와 같은 주식 수
        nxt = {h['cusip']: h for h in qs['2025-09-30']['holdings']}
        self.assertEqual(held[self.HHH]['shares'], 27852064)
        self.assertEqual(held[self.HHH]['shares'], nxt[self.HHH]['shares'])
        # 두 법인이 똑같이 적은 줄은 한 번만
        self.assertEqual(held[self.BETA]['shares'], 500)
        self.assertEqual([d['cusip'] for d in q['merged_dups']], [self.BETA])
        # 예전 번호의 정정은 예전 번호 몫에만 — 하워드 휴즈 합계는 그대로
        self.assertEqual(held[self.GAMMA]['shares'], 10)
        self.assertEqual([a['accession'] for a in q['amended_applied']], ['1111111111-25-000003'])
        self.assertNotIn('total_mismatch', q)
        self.assertNotIn('lines_mismatch', q)
        # 원문은 낸 법인의 폴더에서
        self.assertTrue(any(f'/data/{int(self.OLD)}/111111111125000002/' in u for u in asked))
        self.assertTrue(any(f'/data/{int(self.NEW)}/222222222225000001/' in u for u in asked))

    def test_without_the_merge_flag_the_new_number_still_wins(self):
        # 테퍼처럼 합치지 않는 투자자는 예전 규칙 그대로 — 겹친 분기는 지금 번호 것만.
        code, book, asked = self.run_merge(merge=False)
        q = {q['period']: q for q in book['quarters']}['2025-06-30']
        self.assertNotIn('partners', q)
        self.assertEqual({h['cusip'] for h in q['holdings']}, {self.HHH, self.BETA})
        self.assertFalse(any('111111111125000002' in u for u in asked))

    def late_partner(self, first_hidden):
        # 두 법인이 같은 분기를 며칠 차이로 냅니다 — 첫 실행에는 한쪽만 보입니다.
        with tempfile.TemporaryDirectory() as tmp:
            self.run_merge(hide={*first_hidden, '1111111111-25-000003'}, where=tmp)
            code, book, _ = self.run_merge(where=tmp)
        return code, book

    def test_a_partner_that_arrives_later_is_added_to_the_saved_quarter(self):
        code, book = self.late_partner({'1111111111-25-000002'})
        self.assertEqual(code, 0)
        rows = [q for q in book['quarters'] if q['period'] == '2025-06-30']
        self.assertEqual(len(rows), 1)
        held = {h['cusip']: h for h in rows[0]['holdings']}
        self.assertEqual(held[self.HHH]['shares'], 27852064)
        self.assertEqual([p['accession'] for p in rows[0]['partners']], ['1111111111-25-000002'])

    def test_a_standalone_old_number_quarter_is_replaced_by_the_merged_one(self):
        code, book = self.late_partner({'2222222222-25-000001'})
        self.assertEqual(code, 0)
        rows = [q for q in book['quarters'] if q['period'] == '2025-06-30']
        self.assertEqual([q['accession'] for q in rows], ['2222222222-25-000001'])
        held = {h['cusip']: h for h in rows[0]['holdings']}
        self.assertEqual(held[self.HHH]['shares'], 27852064)
        self.assertEqual(held[self.GAMMA]['shares'], 10)

    def test_a_late_partner_that_cannot_be_read_keeps_the_saved_quarter(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_merge(hide={'1111111111-25-000002', '1111111111-25-000003'}, where=tmp)
            code, book, _ = self.run_merge(where=tmp, docs_patch={'111111111125000002'})
        self.assertEqual(code, 1)
        rows = [q for q in book['quarters'] if q['period'] == '2025-06-30']
        self.assertEqual(len(rows), 1)
        self.assertEqual({h['cusip']: h for h in rows[0]['holdings']}[self.HHH]['shares'], 9000000)

    def test_a_missing_partner_filing_does_not_save_half_a_quarter(self):
        code, book, _ = self.run_merge(docs_patch={'111111111125000002'})
        self.assertEqual(code, 1)
        self.assertNotIn('2025-06-30', {q['period'] for q in book['quarters']})

    def test_registry_reads_the_merge_flag(self):
        spec = importlib.util.spec_from_file_location('reg_for_test', ROOT / 'scripts/titans/registry.py')
        reg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reg)
        base = {'slug': 'x', 'cik': '0000000003', 'filing_name': 'X', 'name': {'en': 'X', 'ko': 'X'},
                'since': 2013, 'active': True}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'r.json'
            path.write_text(json.dumps({'investors': [{**base, 'predecessors': [
                {'cik': '0000000004', 'filing_name': 'Old', 'merge': True}]}]}), encoding='utf8')
            self.assertEqual(reg.load(path)[0].merge_overlap, ('0000000004',))
            path.write_text(json.dumps({'investors': [{**base, 'predecessors': [
                {'cik': '0000000004', 'filing_name': 'Old', 'merge': 'yes'}]}]}), encoding='utf8')
            with self.assertRaises(ValueError):
                reg.load(path)
