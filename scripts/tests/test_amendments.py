"""정정 공시(13F-HR/A) 병합 검사. SEC 요청·실제 데이터 쓰기 없이 실행합니다.

python -m unittest discover -s scripts/tests -p 'test_*.py'

여기 쓰는 XML 모양은 **실물에서 그대로 옮긴 것**입니다. 2026-09-20 에
`probe_amendments.py` 로 버크셔의 XML 시대 정정 8건을 받아 확인했습니다
(run 35482954100). 항목 이름과 값을 짐작해서 만든 것이 아닙니다.
"""
import contextlib
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

NS = 'http://www.sec.gov/edgar/thirteenffiler'
TNS = 'http://www.sec.gov/edgar/document/thirteenf/informationtable'


def cover(*, amend=None, no=None, total=None, lines=None):
    """표지(primary_doc.xml). 실물의 항목 이름을 그대로 씁니다."""
    bits = ['<?xml version="1.0"?>', f'<edgarSubmission xmlns="{NS}"><formData>']
    bits.append('<coverPage><reportCalendarOrQuarter>09-30-2023'
                '</reportCalendarOrQuarter>')
    if amend is not None:
        bits.append('<isAmendment>true</isAmendment><amendmentInfo>'
                    f'<amendmentNo>{no}</amendmentNo>'
                    f'<amendmentType>{amend}</amendmentType>'
                    '<confDeniedExpired>true</confDeniedExpired>'
                    '<reasonForNonConfidentiality>Confidential Treatment Expired'
                    '</reasonForNonConfidentiality></amendmentInfo>')
    bits.append('</coverPage><summaryPage>')
    if total is not None:
        bits.append(f'<tableValueTotal>{total}</tableValueTotal>')
    if lines is not None:
        bits.append(f'<tableEntryTotal>{lines}</tableEntryTotal>')
    bits.append('</summaryPage></formData></edgarSubmission>')
    return ''.join(bits).encode()


def table(rows):
    """정보표. rows 는 (이름, cusip, 금액, 주식수) 입니다."""
    out = [f'<?xml version="1.0"?><informationTable xmlns="{TNS}">']
    for name, cusip, value, shares in rows:
        out.append(f'<infoTable><nameOfIssuer>{name}</nameOfIssuer>'
                   '<titleOfClass>COM</titleOfClass>'
                   f'<cusip>{cusip}</cusip><value>{value}</value>'
                   f'<shrsOrPrnAmt><sshPrnamt>{shares}</sshPrnamt>'
                   '<sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>'
                   '</infoTable>')
    out.append('</informationTable>')
    return ''.join(out).encode()


# 원본 두 줄 · 합계 $30,000
BASE = table([('ALPHA CORP', '111111111', 20000, 100),
              ('BETA CORP', '222222222', 10000, 50)])
# 전체 재작성 — 같은 두 줄인데 알파가 줄었습니다 ($25,000)
RESTATED = table([('ALPHA CORP', '111111111', 15000, 75),
                  ('BETA CORP', '222222222', 10000, 50)])
# 추가 공개분 — 비공개였던 한 줄만 ($7,000)
ADDED = table([('GAMMA CORP', '333333333', 7000, 35)])


class AmendmentMergeTests(unittest.TestCase):
    """`merge_amendments` 자체. 원문 받기만 흉내 냅니다."""

    def merge(self, docs, accs):
        """docs: 접수번호 → (정보표, 표지)"""
        def fake(acc, _contact):
            return docs[acc]
        with patch.object(fetch, 'filing_docs', side_effect=fake):
            base, why = fetch.one_doc('orig', 'fixture')
            self.assertIsNone(why)
            return fetch.merge_amendments(base, accs, 'fixture')

    def test_restatement_replaces_the_original(self):
        got, bad = self.merge({
            'orig': (BASE, cover(total=30000, lines=2)),
            'a1': (RESTATED, cover(amend='RESTATEMENT', no=1, total=25000, lines=2)),
        }, ['a1'])
        self.assertIsNone(bad)
        self.assertEqual(len(got['rows']), 2)
        self.assertEqual(sum(r['value'] for r in got['rows']), 25000)
        # 갈아끼웠으므로 원본의 알파 100주는 남아 있으면 안 됩니다.
        alpha = [r for r in got['rows'] if r['cusip'] == '111111111']
        self.assertEqual([r['shares'] for r in alpha], [75])

    def test_new_holdings_is_added_not_substituted(self):
        got, bad = self.merge({
            'orig': (BASE, cover(total=30000, lines=2)),
            'a1': (ADDED, cover(amend='NEW HOLDINGS', no=1, total=7000, lines=1)),
        }, ['a1'])
        self.assertIsNone(bad)
        self.assertEqual(len(got['rows']), 3)
        self.assertEqual(sum(r['value'] for r in got['rows']), 37000)
        self.assertEqual(got['want_total'], 37000)
        self.assertEqual(got['want_lines'], 3)

    def test_order_follows_amendment_number_not_the_stored_list(self):
        """**이 검사가 이 파일의 이유입니다.**

        실물 2023-09-30 은 저장된 배열이 `[2번, 1번]` 순서였습니다. 배열 순서대로
        적용하면 추가분을 더한 뒤 전체 재작성이 그것을 덮어써서 **뒤늦게 공개된
        줄이 조용히 사라집니다.**"""
        docs = {
            'orig': (BASE, cover(total=30000, lines=2)),
            'no2-added': (ADDED, cover(amend='NEW HOLDINGS', no=2, total=7000, lines=1)),
            'no1-restate': (RESTATED, cover(amend='RESTATEMENT', no=1,
                                            total=25000, lines=2)),
        }
        # 실물과 같은 순서로 넘깁니다 — 2번이 먼저 들어 있습니다.
        got, bad = self.merge(docs, ['no2-added', 'no1-restate'])
        self.assertIsNone(bad)
        self.assertEqual([a['no'] for a in got['applied']], [1, 2])
        cusips = {r['cusip'] for r in got['rows']}
        self.assertIn('333333333', cusips, '추가 공개분이 사라졌습니다')
        self.assertEqual(len(got['rows']), 3)
        self.assertEqual(sum(r['value'] for r in got['rows']), 32000)

    def test_unknown_kind_refuses_to_merge(self):
        for kind in ('SOMETHING ELSE', None):
            with self.subTest(kind=kind):
                got, bad = self.merge({
                    'orig': (BASE, cover(total=30000, lines=2)),
                    'a1': (ADDED, cover(amend=kind, no=1) if kind else cover()),
                }, ['a1'])
                self.assertIsNone(got)
                self.assertIn('종류를 모릅니다', bad)

    def test_missing_original_document_refuses_to_merge(self):
        with patch.object(fetch, 'filing_docs', return_value=(None, None)):
            base, why = fetch.one_doc('orig', 'fixture')
        self.assertIsNone(base)
        self.assertEqual(why, '받지 못함')

    def test_units_are_levelled_before_combining(self):
        """옛 분기는 금액이 **천 달러**입니다. 그대로 더하면 한쪽이 1000배 틀립니다."""
        thousands = table([('ALPHA CORP', '111111111', 20, 100)])   # 20천 = $20,000
        got, bad = self.merge({
            'orig': (thousands, cover(total=20, lines=1)),
            'a1': (ADDED, cover(amend='NEW HOLDINGS', no=1, total=7000, lines=1)),
        }, ['a1'])
        self.assertIsNone(bad)
        self.assertEqual(sum(r['value'] for r in got['rows']), 27000)


class ApplyToBookTests(unittest.TestCase):
    """분기 목록에 실제로 반영되는지. 파일은 안 건드립니다."""

    def quarter(self, **kw):
        q = {'period': '2023-09-30', 'filed': '2023-11-14', 'accession': 'orig',
             'lines': 2, 'unit': 'usd', 'total': 30000,
             'holdings': [{'cusip': '111111111', 'value': 20000}],
             'amended_by': ['a1']}
        q.update(kw)
        return q

    def apply(self, quarters, docs):
        def fake(acc, _contact):
            return docs.get(acc, (None, None))
        with patch.object(fetch, 'filing_docs', side_effect=fake), \
                contextlib.redirect_stdout(io.StringIO()):
            # (반영한 분기 수, 못 합친 분기 목록) 을 돌려줍니다.
            return fetch.apply_amendments(quarters, 'fixture')[0]

    def test_merged_quarter_records_what_was_applied(self):
        q = self.quarter()
        n = self.apply([q], {
            'orig': (BASE, cover(total=30000, lines=2)),
            'a1': (ADDED, cover(amend='NEW HOLDINGS', no=1, total=7000, lines=1)),
        })
        self.assertEqual(n, 1)
        self.assertEqual(q['total'], 37000)
        self.assertEqual(q['lines'], 3)
        self.assertEqual(len(q['holdings']), 3)
        self.assertEqual([a['accession'] for a in q['amended_applied']], ['a1'])
        self.assertEqual(q['amended_applied'][0]['type'], 'NEW HOLDINGS')

    def test_second_run_does_not_fetch_again(self):
        """매주 도는 작업입니다. 이미 반영한 분기를 또 받으면 안 됩니다."""
        q = self.quarter()
        docs = {'orig': (BASE, cover(total=30000, lines=2)),
                'a1': (ADDED, cover(amend='NEW HOLDINGS', no=1, total=7000, lines=1))}
        self.assertEqual(self.apply([q], docs), 1)
        snapshot = json.dumps(q, sort_keys=True)

        calls = []

        def counting(acc, _contact):
            calls.append(acc)
            return docs.get(acc, (None, None))
        with patch.object(fetch, 'filing_docs', side_effect=counting), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fetch.apply_amendments([q], 'fixture'), (0, []))
        self.assertEqual(calls, [], '이미 반영했는데 원문을 다시 받았습니다')
        self.assertEqual(json.dumps(q, sort_keys=True), snapshot)

    def test_a_new_amendment_later_triggers_a_rebuild(self):
        q = self.quarter()
        docs = {'orig': (BASE, cover(total=30000, lines=2)),
                'a1': (ADDED, cover(amend='NEW HOLDINGS', no=1, total=7000, lines=1))}
        self.assertEqual(self.apply([q], docs), 1)
        # 나중에 전체 재작성이 하나 더 떴습니다.
        q['amended_by'] = ['a1', 'a2']
        docs['a2'] = (RESTATED, cover(amend='RESTATEMENT', no=2,
                                      total=25000, lines=2))
        self.assertEqual(self.apply([q], docs), 1)
        # 2번이 전체 재작성이므로 1번의 추가분은 덮입니다 — 그것이 공시의 뜻입니다.
        self.assertEqual(q['total'], 25000)
        self.assertEqual([a['no'] for a in q['amended_applied']], [1, 2])

    def test_pre_xml_quarter_is_marked_once_and_left_alone(self):
        """2013년 중반 이전은 텍스트 공시라 자동으로 못 합칩니다.

        사용자가 **투자자별 일회성 변환**으로 확정한 영역입니다(`CLAUDE.md`
        9-3-1). 한 번 적어 두고 다시 받지 않습니다 — 안 그러면 매주 수십 건을
        헛되이 받습니다."""
        q = self.quarter(period='2005-06-30', total=999)
        before = dict(q['holdings'][0])
        self.assertEqual(self.apply([q], {'orig': (fetch.NO_XML, None)}), 0)
        self.assertEqual(q['amend_gap'], 'pre-xml')
        self.assertEqual(q['total'], 999, '원본 숫자를 건드렸습니다')
        self.assertEqual(q['holdings'][0], before)

        calls = []

        def counting(acc, _contact):
            calls.append(acc)
            return (fetch.NO_XML, None)
        with patch.object(fetch, 'filing_docs', side_effect=counting), \
                contextlib.redirect_stdout(io.StringIO()):
            fetch.apply_amendments([q], 'fixture')
        self.assertEqual(calls, [], '못 합치는 분기를 다시 받았습니다')

    def test_refusal_leaves_the_quarter_exactly_as_it_was(self):
        """반쯤 합친 분기를 남기는 것보다 안 합친 것이 낫습니다."""
        q = self.quarter()
        before = json.dumps(q, sort_keys=True)
        n = self.apply([q], {
            'orig': (BASE, cover(total=30000, lines=2)),
            'a1': (ADDED, cover()),          # 표지에 종류가 없습니다
        })
        self.assertEqual(n, 0)
        self.assertEqual(json.dumps(q, sort_keys=True), before)

    def test_quarter_without_amendments_is_never_touched(self):
        q = self.quarter(amended_by=[])
        before = json.dumps(q, sort_keys=True)
        self.assertEqual(self.apply([q], {}), 0)
        self.assertEqual(json.dumps(q, sort_keys=True), before)


if __name__ == '__main__':
    unittest.main()
