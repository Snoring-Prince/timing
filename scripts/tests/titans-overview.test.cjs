const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const vm=require('node:vm');
const overview=require('../../titans/shared/overview.js');
const {publish,replaceOverview,removeOverview}=require('../publish_titans_overviews.cjs');
const root=path.resolve(__dirname,'../..');
const investor={slug:'sample',cik:'0000000001',name:{en:'Sample Fund',ko:'샘플 펀드'}};
const holding=(cusip='123456100',value=100,extra={})=>({cusip,value,name:'SAMPLE CORP',shares:10,class:'COM',...extra});
const q=(period,holdings)=>({period,filed:'2026-08-14',holdings});
const book=quarters=>({manager:{cik:investor.cik},quarters});

test('stock scope, share classes, preferred shares and weights agree with the live renderer for every investor',()=>{
  const core=fs.readFileSync(path.join(root,'titans/shared/investor.js'),'utf8').split('/* 곁들이 표 둘')[0];
  const registry=JSON.parse(fs.readFileSync(path.join(root,'data/titans/investors.json'),'utf8'));
  for(const inv of registry.investors.filter(i=>i.active!==false)){
    const data=JSON.parse(fs.readFileSync(path.join(root,`data/titans/${inv.slug}.json`),'utf8'));
    const ctx={window:{TITAN:inv},console,document:{},data,URLSearchParams};
    vm.createContext(ctx);vm.runInContext(core,ctx);
    const rows=JSON.parse(vm.runInContext(`JSON.stringify([...merge(data.quarters.at(-1)).values()].sort((a,b)=>b.value-a.value||a.key.localeCompare(b.key)).map(r=>({key:r.key,name:title(r.name),value:r.value,cusip:r.cusip})))`,ctx));
    const pricefile=path.join(root,`data/titans/prices/${inv.slug}.json`);
    const prices=fs.existsSync(pricefile)?JSON.parse(fs.readFileSync(pricefile,'utf8')):null;
    const tickers=overview.tickersFrom(prices);
    const s=overview.summarize(data,tickers), total=rows.reduce((sum,r)=>sum+r.value,0);
    assert.equal(s.stocks,rows.length,inv.slug);
    assert.deepEqual(s.top.map(({tickers,...r})=>r),rows.slice(0,3).map(({cusip,...r})=>({...r,weight:total?r.value/total*100:null})),inv.slug);
    // Tickers: the same filter as the page's price loader, and the ticker the page
    // draws for a row (its largest class) is always among the summary's tickers.
    ctx.prices=prices;vm.runInContext('acceptPrices(prices)',ctx);
    const page=JSON.parse(vm.runInContext('JSON.stringify(Object.fromEntries(Object.entries(PRICE_SERIES).map(([k,v])=>[k,v.ticker])))',ctx));
    assert.deepEqual(tickers,page,inv.slug);
    s.top.forEach((r,i)=>{ if(page[rows[i].cusip])assert.ok(r.tickers.includes(page[rows[i].cusip]),`${inv.slug} ${r.name}`); });
    const html=fs.readFileSync(path.join(root,`titans/${inv.slug}/index.html`),'utf8');
    assert.ok(html.includes(`prices: "../../data/titans/prices/${inv.slug}.json"`),inv.slug);
    assert.ok(html.includes(overview.section(data,inv,tickers)),`${inv.slug}: static and live summaries differ`);
  }
});
test('options and principal are excluded, common classes merged and preferred kept separate',()=>{
  const s=overview.summarize(book([q('2026-06-30',[
    holding(),holding('123456200',50),holding('123456300',25,{class:'PFD'}),
    holding('123456400',10000,{putCall:'CALL'}),holding('123456500',10000,{type:'PRN'})])]));
  assert.equal(s.stocks,2);assert.equal(s.top[0].value,150);assert.equal(s.top[1].key,'123456|P');
  assert.equal(s.top[0].weight,150/175*100);
});
test('first filing never implies new purchases; gaps always name the actual comparison quarter',()=>{
  const first=book([q('2026-06-30',[holding()])]);
  assert.deepEqual(overview.summarize(first).appeared,[]);
  assert.match(overview.content(first,investor),/이전 공시가 없어/);
  const gap=book([q('2025-12-31',[]),q('2026-06-30',[holding()])]);
  const html=overview.content(gap,investor);
  assert.match(html,/2025년 4분기 공시와 비교/);assert.match(html,/Q4 2025 filing/);
  assert.doesNotMatch(html,/직전 분기|previous quarter|신규 매수|purchased/);
});
test('splits and class substitutions cannot produce an entry or disappearance',()=>{
  const data=book([q('2026-03-31',[holding()]),q('2026-06-30',[holding('123456200',100,{shares:20})])]);
  const s=overview.summarize(data);assert.deepEqual(s.appeared,[]);assert.deepEqual(s.absent,[]);
  assert.match(overview.content(data,investor),/수량·비중 변화/);
});
test('re-entry is reported as newly present, and disappearance is not called an executed sale',()=>{
  const data=book([q('2025-12-31',[holding()]),q('2026-03-31',[holding('654321100')]),q('2026-06-30',[holding()])]);
  const s=overview.summarize(data);assert.equal(s.appeared[0].key,'123456');assert.equal(s.absent[0].key,'654321');
  const text=overview.content(data,investor);assert.match(text,/새로 나타난/);assert.match(text,/No longer reported/);
  assert.doesNotMatch(text,/신규 매수|전량매도|bought|sold/);
});
test('many changes show the largest two with an honest remaining count, not an exhaustive-looking list',()=>{
  const data=book([q('2026-03-31',[]),q('2026-06-30',Array.from({length:5},(_,i)=>holding(`00000${i}100`,i+1,{name:`Company ${i}`})))]);
  const html=overview.content(data,investor);
  assert.match(html,/Newly present: Company 4, Company 3 and 3 more/);
  assert.match(html,/새로 나타난 종목은 Company 4, Company 3 외 3종목/);
});
test('empty and zero-value filings never produce NaN or an invented weight',()=>{
  assert.doesNotMatch(overview.content(book([q('2026-06-30',[])]),investor),/NaN|Infinity/);
  const html=overview.content(book([q('2026-06-30',[holding('123456100',0)])]),investor);
  assert.doesNotMatch(html,/NaN|Infinity|\(0.0%\)/);
});
test('untrusted names are escaped in both languages and bad or duplicate periods are rejected',()=>{
  const html=overview.content(book([q('2026-06-30',[holding('123456100',100,{name:'<img src=x onerror=alert(1)>'})])]),investor);
  assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img'));
  assert.throws(()=>overview.summarize(book([q('2026-06-30',[]),q('2026-06-30',[])])),/unordered/);
  assert.throws(()=>overview.summarize(book([q('2026-06-31',[])])),/Invalid/);
  assert.throws(()=>overview.summarize(book([q('2026-06-30',[holding('123456100',-1)])])),/Invalid/);
});

function fixture(t){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'titans-overview-'));
  t.after(()=>{
    const relative=path.relative(path.resolve(os.tmpdir()),path.resolve(dir));
    assert.ok(!relative.startsWith('..')&&!path.isAbsolute(relative)&&relative.startsWith('titans-overview-'));
    fs.rmSync(dir,{recursive:true,force:true});
  });
  fs.mkdirSync(path.join(dir,'data/titans'),{recursive:true});fs.mkdirSync(path.join(dir,'titans/sample'),{recursive:true});
  fs.writeFileSync(path.join(dir,'data/titans/investors.json'),JSON.stringify({investors:[investor]}));
  const file=path.join(dir,'titans/sample/index.html');
  fs.writeFileSync(file,'<main id="static-investor"><p>Biography stays</p></main><script src="../shared/overview.js?v=fixture"></script>');
  const datafile=path.join(dir,'data/titans/sample.json');
  fs.writeFileSync(datafile,JSON.stringify(book([q('2026-06-30',[holding()])])));
  return {dir,file,datafile};
}
test('a newly registered investor publishes without special cases; repeat writes and check mode are inert',t=>{
  const {dir,file}=fixture(t);assert.deepEqual(publish(dir),['sample']);
  const first=fs.readFileSync(file,'utf8'),mtime=fs.statSync(file).mtimeMs;
  assert.match(first,/Biography stays/);assert.match(first,/샘플 펀드/);assert.match(first,/Sample Fund/);
  assert.deepEqual(publish(dir),[]);assert.deepEqual(publish(dir,{check:true}),[]);
  assert.equal(fs.statSync(file).mtimeMs,mtime);
});
test('same-quarter corrections and new quarters replace both languages; --check does not write',t=>{
  const {dir,file,datafile}=fixture(t);publish(dir);const old=fs.readFileSync(file,'utf8');
  const data=book([q('2026-06-30',[holding(),holding('654321100',300,{name:'Corrected Company'})])]);
  fs.writeFileSync(datafile,JSON.stringify(data));
  assert.throws(()=>publish(dir,{check:true}),/Stale/);assert.equal(fs.readFileSync(file,'utf8'),old);
  publish(dir);assert.match(fs.readFileSync(file,'utf8'),/Corrected Company \(75.0%\)/);
  data.quarters.push({...q('2026-09-30',[]),filed:'2026-11-13'});fs.writeFileSync(datafile,JSON.stringify(data));publish(dir);
  const html=fs.readFileSync(file,'utf8');assert.match(html,/2026년 3분기/);assert.match(html,/Q3 2026/);
  assert.equal(html.split('id="filing-overview"').length,2);
});
function addInvestor(dir,inv,html,data){
  const registry=JSON.parse(fs.readFileSync(path.join(dir,'data/titans/investors.json'),'utf8'));
  registry.investors.push(inv);fs.writeFileSync(path.join(dir,'data/titans/investors.json'),JSON.stringify(registry));
  fs.mkdirSync(path.join(dir,`titans/${inv.slug}`),{recursive:true});
  const file=path.join(dir,`titans/${inv.slug}/index.html`);fs.writeFileSync(file,html);
  if(data)fs.writeFileSync(path.join(dir,`data/titans/${inv.slug}.json`),JSON.stringify(data));
  return file;
}
test('a bad book keeps only that page\'s snapshot; the other investors still update and the run fails',t=>{
  const {dir,file,datafile}=fixture(t);publish(dir);const old=fs.readFileSync(file,'utf8');
  const other={slug:'other',cik:'0000000003',name:{en:'Other Fund',ko:'다른 펀드'}};
  const otherFile=addInvestor(dir,other,'<main id="static-investor"></main><script src="../shared/overview.js?v=fixture"></script>',
    {manager:{cik:other.cik},quarters:[q('2026-06-30',[holding('654321100',100,{name:'OTHER HOLDING'})])]});
  const wrong=book([q('2026-09-30',[])]);wrong.manager.cik='0000000002';fs.writeFileSync(datafile,JSON.stringify(wrong));
  assert.throws(()=>publish(dir,{check:true}),/sample: Investor CIK mismatch[\s\S]*Stale investor overviews: other/);
  assert.throws(()=>publish(dir),/CIK mismatch[\s\S]*Updated overviews: other/);
  assert.equal(fs.readFileSync(file,'utf8'),old);assert.match(fs.readFileSync(otherFile,'utf8'),/Other Holding/);
  fs.writeFileSync(datafile,JSON.stringify(book([q('2026-06-30',[holding('123456100',1,{name:''})])])));
  assert.throws(()=>publish(dir),/sample: Invalid overview holding/);assert.equal(fs.readFileSync(file,'utf8'),old);
});
test('an investor registered before its first filing shows no summary, never a copied one, and fails nothing',t=>{
  const {dir,file}=fixture(t);publish(dir);
  // Registering by copying another investor's page brings that investor's snapshot along.
  const copied=fs.readFileSync(file,'utf8').replace('Biography stays','New biography');
  const fresh={slug:'fresh',cik:'0000000004',name:{en:'Fresh Fund',ko:'새 펀드'}};
  const freshFile=addInvestor(dir,fresh,copied);
  assert.match(copied,/Sample Fund/);
  assert.throws(()=>publish(dir,{check:true}),/Stale investor overviews: fresh/);
  assert.deepEqual(publish(dir),['fresh']);
  const html=fs.readFileSync(freshFile,'utf8');
  assert.doesNotMatch(html,/filing-overview|TITAN-OVERVIEW|Sample Fund|샘플 펀드/);
  assert.match(html,/New biography<\/p><\/main>/);
  assert.deepEqual(publish(dir),[]);assert.deepEqual(publish(dir,{check:true}),[]);
  // Its first filing then publishes into the same shell with no special case.
  fs.writeFileSync(path.join(dir,'data/titans/fresh.json'),JSON.stringify({manager:{cik:fresh.cik},quarters:[q('2026-06-30',[holding()])]}));
  assert.deepEqual(publish(dir),['fresh']);assert.match(fs.readFileSync(freshFile,'utf8'),/Fresh Fund reports 1 US-listed/);
  assert.throws(()=>removeOverview('<!-- TITAN-OVERVIEW:START -->'),/markers/);
});
test('a lost book (its price file still there) is a failure that keeps the page, not a reset to no summary',t=>{
  const {dir,file,datafile}=fixture(t);publish(dir);const old=fs.readFileSync(file,'utf8');
  fs.mkdirSync(path.join(dir,'data/titans/prices'));fs.writeFileSync(path.join(dir,'data/titans/prices/sample.json'),'{}');
  fs.rmSync(datafile);
  assert.throws(()=>publish(dir),/sample: Filing book missing while its price file exists/);
  assert.equal(fs.readFileSync(file,'utf8'),old);assert.match(old,/filing-overview/);
});
const priceBook=series=>({method:'split-adjusted-close',series});
const priced=(ticker,extra={})=>({ticker,currency:'USD',values:[['2026-06-30',10]],...extra});
test('tickers name every priced class of a merged row, largest first, and are omitted when unknown',()=>{
  const data=book([q('2026-03-31',[holding('999999100',1,{name:'GONE CORP'})]),q('2026-06-30',[
    holding('123456100',40,{name:'ALPHABET INC',class:'CAP STK CL A'}),holding('123456200',60,{name:'ALPHABET INC',class:'CAP STK CL C'}),
    holding('654321100',50,{name:'PLAIN CORP'}),holding('777777100',10,{name:'NO PRICE CORP'})])]);
  const tickers={'123456100':'GOOGL','123456200':'GOOG','654321100':'PL<b>N','999999100':'GONE'};
  const s=overview.summarize(data,tickers);
  assert.deepEqual(s.top.map(r=>r.tickers),[['GOOG','GOOGL'],['PLbN'],[]]);
  const html=overview.content(data,investor,tickers);
  assert.match(html,/largest 3 positions are Alphabet Inc \(GOOG\/GOOGL, 62\.5%\), Plain Corp \(PLbN, 31\.3%\) and No Price Corp \(6\.3%\)\./);
  assert.match(html,/상위 3종목은 Alphabet Inc \(GOOG\/GOOGL, 62\.5%\), Plain Corp \(PLbN, 31\.3%\), No Price Corp \(6\.3%\)입니다/);
  assert.match(html,/No longer reported: Gone Corp \(GONE\)\./);
  assert.doesNotMatch(html,/<b>/);
  assert.deepEqual(overview.summarize(data).top[0].tickers,[]);
  assert.doesNotMatch(overview.content(data,investor),/GOOG/);
});
test('ticker reading follows the page\'s price loader: wrong method, currency, keys or empty closes give no ticker',()=>{
  assert.deepEqual(overview.tickersFrom(null),{});assert.deepEqual(overview.tickersFrom({series:{}}),{});
  assert.deepEqual(overview.tickersFrom({method:'close',series:{'123456100':priced('AAA')}}),{});
  assert.deepEqual(overview.tickersFrom(priceBook({
    '123456100':priced('AAA'),'223456100':priced('BBB',{currency:'EUR'}),'323456100':priced('CCC',{values:[['2026-02-30',10],['2026-06-30',0]]}),
    'bad key':priced('DDD'),'423456100':priced(7),'523456100':priced('LEN-B'),'623456100':priced('<>')})),{'123456100':'AAA','523456100':'LEN-B'});
});
test('the publisher reads tickers from the page\'s own price file; a missing or broken file only drops them',t=>{
  const {dir,file}=fixture(t);
  fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace('<main','<script>window.TITAN={prices: "../../data/titans/prices/sample.json"}</script><main'));
  publish(dir);assert.match(fs.readFileSync(file,'utf8'),/Sample Corp \(100\.0%\)/);
  fs.mkdirSync(path.join(dir,'data/titans/prices'));const pf=path.join(dir,'data/titans/prices/sample.json');
  fs.writeFileSync(pf,JSON.stringify(priceBook({'123456100':priced('SMPL')})));
  // A new ticker from the price run makes the page stale until it is published again.
  assert.throws(()=>publish(dir,{check:true}),/Stale investor overviews: sample/);
  publish(dir);assert.match(fs.readFileSync(file,'utf8'),/Sample Corp \(SMPL, 100\.0%\)/);
  fs.writeFileSync(pf,'{broken');assert.deepEqual(publish(dir),['sample']);
  assert.match(fs.readFileSync(file,'utf8'),/Sample Corp \(100\.0%\)/);
  // A page set to read another file never gets this file's tickers.
  fs.writeFileSync(pf,JSON.stringify(priceBook({'123456100':priced('SMPL')})));
  fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace('prices/sample.json','prices/other.json'));
  publish(dir);assert.match(fs.readFileSync(file,'utf8'),/Sample Corp \(100\.0%\)/);
});
test('damaged or duplicated markers never overwrite surrounding page content',()=>{
  assert.throws(()=>replaceOverview('<!-- TITAN-OVERVIEW:START -->','new'),/markers/);
  assert.throws(()=>replaceOverview('<!-- TITAN-OVERVIEW:END --><!-- TITAN-OVERVIEW:START -->','new'),/markers/);
  assert.throws(()=>replaceOverview('<main></main>','new'),/shell/);
});
test('workflow publishes and saves HTML after filings and includes failures in the Telegram path',()=>{
  const wf=fs.readFileSync(path.join(root,'.github/workflows/update-13f.yml'),'utf8');
  assert.ok(wf.indexOf('scripts/watch_13f.py')<wf.indexOf('node scripts/publish_titans_overviews.cjs'));
  assert.ok(wf.indexOf('node scripts/publish_titans_overviews.cjs')<wf.indexOf('git add titans/*/index.html'));
  assert.match(wf,/steps.overviews.outcome == 'failure'/);assert.match(wf,/overview-publish.log >> 13f-error.txt/);
});
test('the price workflow republishes ticker changes on the latest main, saves them and alerts on failure',()=>{
  const wf=fs.readFileSync(path.join(root,'.github/workflows/update-prices.yml'),'utf8');
  const at=s=>{const i=wf.indexOf(s);assert.ok(i>=0,s);return i;};
  assert.ok(at('git push origin HEAD:main')<at('git pull --rebase origin main\n          node scripts/publish_titans_overviews.cjs'));
  assert.ok(at('node scripts/publish_titans_overviews.cjs')<at('git add titans/*/index.html'));
  assert.match(wf,/id: overviews\n\s+if: always\(\) && steps.fetch.outcome != 'skipped'/);
  assert.match(wf,/set -o pipefail\n\s+git pull --rebase origin main\n\s+node scripts\/publish_titans_overviews.cjs 2>&1 \| tee overview-publish.log/);
  assert.match(wf,/OVERVIEW_RESULT: \$\{\{ steps.overviews.outcome \}\}/);assert.match(wf,/tail -n 10 overview-publish.log/);
  assert.match(wf,/node-version: "22"/);
});
