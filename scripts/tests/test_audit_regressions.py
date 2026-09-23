"""Multi-investor audit regressions. No external requests or production writes."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch_13f as f
import fetch_prices as prices
import fetch_sectors as sectors
import fetch_tickers as tickers
import watch_13f as watch
from titans import registry
from test_amendments import table, cover


class UnitsTests(unittest.TestCase):
    def test_price_level_cannot_choose_the_dollar_unit(self):
        # Modern penny stocks and old >$1,000 stocks both defeat the median heuristic.
        rows = [{'type': 'SH', 'shares': 100, 'value': 50}]
        self.assertEqual(f.unit_scale(rows, '2023-01-03')[0], 1)
        rows[0]['value'] = 200
        self.assertEqual(f.unit_scale(rows, '2022-12-30')[0], 1000)
        self.assertEqual(f.unit_scale([], '2022-12-30')[0], 1000)

    def test_unknown_date_refuses_to_publish_a_guessed_amount(self):
        with patch.object(f, 'filing_docs', return_value=(table([('X','123456789',50,100)]), cover())):
            doc, why = f.one_doc('unknown-date', 'fixture')
        self.assertIsNone(doc)
        self.assertIn('제출일', why)

    def test_late_amendment_to_an_old_quarter_uses_its_own_filing_date(self):
        docs = {'base': (table([('X','123456789',200,100)]),cover(total=200,lines=1)),
                'amend': (table([('Y','222222222',50,100)]),cover(amend='NEW HOLDINGS',no=1,total=50,lines=1))}
        q = {'period':'2022-09-30','filed':'2022-11-14','accession':'base','amended_by':['amend']}
        with patch.object(f,'filing_docs',side_effect=lambda acc,_:docs[acc]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(f.apply_amendments([q],'fixture',{'amend':'2025-01-08'}),(1,[]))
        self.assertEqual(q['total'],200050)


class SkippedFilingsTests(unittest.TestCase):
    def test_old_text_and_amendment_are_discovered_once_without_fake_quarters(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'book.json'
            inv=SimpleNamespace(output=out,since=2013,name={'ko':'샘플'})
            recent={'period':'2026-03-31','filed':'2026-05-14','accession':'recent'}
            old={'period':'2013-03-31','filed':'2013-05-14','accession':'text'}
            amendment={**old,'accession':'text-amend'}
            ignored={**old,'period':'2012-12-31','accession':'outside'}
            out.write_text(json.dumps({'quarters':[{**recent,'holdings':[],'total':0}]}),encoding='utf-8')
            with patch.dict(os.environ,{'SEC_CONTACT':'fixture'}), patch.object(f,'configure',return_value=inv), \
                 patch.object(f,'OUT',str(out)), patch.object(f,'ALERT',str(Path(tmp)/'alert.txt')), \
                 patch.object(f,'list_filings',return_value=([ignored,old,recent],[amendment])), \
                 patch.object(f,'filing_docs',return_value=(f.NO_XML,None)) as fetch, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(f.main('sample'),0)
                self.assertEqual(fetch.call_count,2)
                first=out.read_bytes()
                fetch.reset_mock()
                self.assertEqual(f.main('sample'),0)
                fetch.assert_not_called()
                self.assertEqual(first,out.read_bytes())
            book=json.loads(first)
            self.assertEqual(len(book['quarters']),1)
            self.assertEqual(len(book['skipped_filings']),2)
            self.assertEqual(watch.changed(inv,[recent,old,amendment,ignored]),[])
            # A genuinely new amendment is still detected.
            new={**amendment,'accession':'later'}
            self.assertEqual(watch.changed(inv,[new]),[new])

    def test_failed_text_request_is_not_recorded_as_intentionally_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'book.json'
            prev={'quarters':[{'period':'2026-03-31','accession':'known','holdings':[]}]}
            out.write_text(json.dumps(prev),encoding='utf-8')
            before=out.read_bytes()
            row={'period':'2013-03-31','filed':'2013-05-14','accession':'unknown'}
            with patch.dict(os.environ,{'SEC_CONTACT':'fixture'}),patch.object(f,'OUT',str(out)), \
                 patch.object(f,'list_filings',return_value=([row],[])), \
                 patch.object(f,'filing_docs',return_value=(None,None)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(f.main(),1)
            self.assertEqual(before,out.read_bytes())


class BookSafetyTests(unittest.TestCase):
    def test_one_missing_active_book_preserves_both_investors_price_cache(self):
        for missing in [True,False]:
            with self.subTest(missing=missing),tempfile.TemporaryDirectory() as tmp:
                a,b,out=(Path(tmp)/name for name in ['a.json','b.json','prices.json'])
                a.write_text(json.dumps({'quarters':[{'period':'2026-03-31','holdings':[
                    {'cusip':'123456789','shares':10,'value':100,'name':'A'}]}]}),encoding='utf-8')
                if not missing:
                    b.write_text('{"quarters":[]}',encoding='utf-8')
                out.write_text('{"series":{"123456789":{},"987654321":{}}}',encoding='utf-8')
                before=out.read_bytes()
                invs=[SimpleNamespace(output=a),SimpleNamespace(output=b)]
                with patch.object(registry,'load',return_value=invs),patch.object(prices,'OUT',out), \
                     patch.object(sys,'argv',['fetch_prices.py']),patch.object(prices,'request') as request:
                    with self.assertRaises(ValueError):
                        prices.main()
                    request.assert_not_called()
                self.assertEqual(out.read_bytes(),before)

    def test_options_and_principal_are_not_requested_as_stock_prices_or_labels(self):
        share={'cusip':'H1467J104','name':'Chubb','value':100,'shares':10}
        option={**share,'cusip':'G01767105','putCall':'CALL'}
        principal={**share,'cusip':'123456789','type':'PRN'}
        book={'quarters':[{'period':'2026-03-31','holdings':[share,option,principal]}]}
        self.assertEqual(set(prices.required_cusips([book])),{'H1467J104'})
        self.assertEqual(set(prices.first_seen([book])),{'H1467J104'})
        self.assertEqual(tickers.wanted_tickers([book])[0],{'H1467J104'})
        self.assertEqual(set(sectors.issuer_names([book])),{'H1467J'})


class AuxiliaryRetryTests(unittest.TestCase):
    def test_sec_company_dictionary_and_figi_array_are_parsed_independently(self):
        payload={'0':{'cik_str':896159,'ticker':'CB','title':'Chubb Limited'}}
        response=io.BytesIO(json.dumps(payload).encode())
        response.headers={}
        with patch.object(tickers.urllib.request,'urlopen',return_value=response), contextlib.redirect_stdout(io.StringIO()):
            index=tickers.sec_index('fixture')
        self.assertEqual(tickers.sec_lookup(index,'Chubb Limited')[0],'CB')
        response=io.BytesIO(json.dumps([{'data':[{'ticker':'CB','exchCode':'US'}]}]).encode())
        response.status=200
        with patch.object(tickers.urllib.request,'urlopen',return_value=response):
            self.assertEqual(tickers.ask(['H1467J104'])[0],{'H1467J104':'CB'})

    def test_incomplete_or_failed_figi_responses_are_not_cached_as_not_found(self):
        for payload in [[], {'error':'timeout'}, [{'error':'server failed'}]]:
            with self.subTest(payload=payload):
                response=io.BytesIO(json.dumps(payload).encode())
                response.status=200
                with patch.object(tickers.urllib.request,'urlopen',return_value=response),self.assertRaises(ValueError):
                    tickers.ask(['H1467J104'])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)/'labels.json'
        self.books=[{'quarters':[{'period':'2026-03-31','holdings':[
            {'cusip':'H1467J104','name':'CHUBB'}, {'cusip':'G01767105','name':'AON'}]}]}]

    def run_tickers(self, ask, lookup=None, contact='fixture'):
        with patch.dict(os.environ,{'SEC_CONTACT':contact}),patch.object(tickers,'OUT',self.out), \
             patch.object(tickers,'books',return_value=self.books),patch.object(tickers,'ask',side_effect=ask) as calls, \
             patch.object(tickers,'BATCH',1),patch.object(tickers.time,'sleep'), \
             patch.object(tickers,'sec_index',return_value={}), \
             patch.object(tickers,'sec_lookup',side_effect=lookup or (lambda *_:('','',''))), \
             contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            result=tickers.main()
        return result,calls

    def test_partial_ticker_failure_is_red_and_retried_on_the_next_run(self):
        def flaky(cs,_):
            if cs==['G01767105']: raise TimeoutError('fixture')
            return {'H1467J104':'CB'},'fixture'
        self.assertEqual(self.run_tickers(flaky)[0],1)
        data=json.loads(self.out.read_text())
        self.assertEqual(data['H1467J104'],'CB')
        self.assertNotIn('G01767105',data)
        self.assertEqual(data['_retry'],['G01767105'])
        result,calls=self.run_tickers(lambda cs,_:({cs[0]:'AON'},'fixture'))
        self.assertEqual(result,0)
        self.assertEqual(calls.call_args[0][0],['G01767105'])
        self.assertNotIn('_retry',json.loads(self.out.read_text()))

    def test_successful_fallback_recovers_failed_ticker_request(self):
        self.assertEqual(self.run_tickers(lambda *_: (_ for _ in ()).throw(TimeoutError()),
                                         lookup=lambda _idx,name:(name,'','1'))[0],0)
        self.assertNotIn('_retry',json.loads(self.out.read_text()))

    def test_confirmed_unknown_tickers_are_cached_not_retried_immediately(self):
        self.assertEqual(self.run_tickers(lambda *_:({},'not found'))[0],0)
        result,calls=self.run_tickers(lambda *_:self.fail('cached unknown requested'))
        self.assertEqual(result,0)
        calls.assert_not_called()

    def run_sectors(self, sic, lookup=None):
        with patch.dict(os.environ,{'SEC_CONTACT':'fixture'}),patch.object(sectors,'OUT',self.out), \
             patch.object(sectors,'books',return_value=self.books),patch.object(sectors,'sic_of',side_effect=sic) as calls, \
             patch.object(sectors.time,'sleep'),patch.object(sectors,'sec_index',return_value={}), \
             patch.object(sectors,'sec_lookup',side_effect=lookup or (lambda _idx,name:('',name,name))), \
             contextlib.redirect_stdout(io.StringIO()):
            result=sectors.main()
        return result,calls

    def test_partial_sector_failure_is_saved_and_retried_without_a_new_filing(self):
        # sic_of returns numeric CIKs in production; map the names explicitly.
        lookup=lambda _,name:('',name,'1' if name=='CHUBB' else '2')
        def first(cik,_):
            if cik=='2': raise TimeoutError('fixture')
            return ('6331','Insurance'),'fixture'
        self.assertEqual(self.run_sectors(first,lookup)[0],1)
        data=json.loads(self.out.read_text())
        self.assertEqual(data['H1467J']['sic'],'6331')
        self.assertNotIn('G01767',data)
        self.assertEqual(data['_retry'],['G01767'])
        result,calls=self.run_sectors(lambda *_:(('6411','Agents'),'fixture'),lookup)
        self.assertEqual(result,0)
        self.assertEqual(calls.call_count,1)
        self.assertNotIn('_retry',json.loads(self.out.read_text()))

    def test_all_names_unknown_is_not_a_network_failure(self):
        result,calls=self.run_sectors(lambda *_:self.fail('no CIK'),lambda *_:('','',''))
        self.assertEqual(result,0)
        calls.assert_not_called()
        self.assertNotIn('_retry',json.loads(self.out.read_text()))
        result,calls=self.run_sectors(lambda *_:self.fail('cached unknown requested'))
        self.assertEqual(result,0)
        calls.assert_not_called()


if __name__=='__main__':
    unittest.main()
