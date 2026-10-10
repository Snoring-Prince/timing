const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const vm=require('node:vm');
const overview=require('../../titans/shared/overview.js');
const {publish,replaceOverview}=require('../publish_titans_overviews.cjs');
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
    const rows=JSON.parse(vm.runInContext(`JSON.stringify([...merge(data.quarters.at(-1)).values()].sort((a,b)=>b.value-a.value||a.key.localeCompare(b.key)).map(r=>({key:r.key,name:title(r.name),value:r.value})))`,ctx));
    const s=overview.summarize(data), total=rows.reduce((sum,r)=>sum+r.value,0);
    assert.equal(s.stocks,rows.length,inv.slug);
    assert.deepEqual(s.top,rows.slice(0,3).map(r=>({...r,weight:total?r.value/total*100:null})),inv.slug);
    const html=fs.readFileSync(path.join(root,`titans/${inv.slug}/index.html`),'utf8');
    assert.ok(html.includes(overview.section(data,inv)),`${inv.slug}: static and live summaries differ`);
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
test('missing or wrong-investor books preserve all existing snapshots and report failure',t=>{
  const {dir,file,datafile}=fixture(t);publish(dir);const old=fs.readFileSync(file,'utf8');
  const wrong=book([q('2026-09-30',[])]);wrong.manager.cik='0000000002';fs.writeFileSync(datafile,JSON.stringify(wrong));
  assert.throws(()=>publish(dir),/CIK mismatch/);assert.equal(fs.readFileSync(file,'utf8'),old);
  fs.writeFileSync(datafile,JSON.stringify(book([q('2026-09-30',[])])));
  fs.writeFileSync(path.join(dir,'data/titans/investors.json'),JSON.stringify({investors:[investor,{...investor,slug:'missing'}]}));
  assert.throws(()=>publish(dir),/missing:/);assert.equal(fs.readFileSync(file,'utf8'),old);
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
