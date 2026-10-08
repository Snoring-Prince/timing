const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const M=require('../../samuel/model.js'),root=path.resolve(__dirname,'../..');
const DAY=86400000,near=(a,b)=>assert.ok(Math.abs(a-b)<1e-7,`${a} differs from ${b}`);
function rows(price=()=>100,reserve=()=>100){const out=[];for(let t=Date.parse('2018-01-01');t<=Date.parse('2025-12-31');t+=DAY){const d=new Date(t);if(d.getUTCDay()>0&&d.getUTCDay()<6)out.push([d.toISOString().slice(0,10),price(out.length,d),reserve(out.length,d)]);}return out;}
const settings={amount:12000,months:6,years:1};

test('flat stock and BIL: same principal is conserved on every day',()=>{
  const result=M.simulate(rows(),'2020-01',settings);
  assert.equal(result.buys.length,6);near(result.buys.reduce((s,r)=>s+r.amount,0),12000);
  for(const p of result.curve){near(p.lump,12000);near(p.split,12000);}
  near(result.reserve,0);near(result.mddL,0);near(result.mddS,0);
});
test('rising and falling markets give opposite rankings without assuming a winner',()=>{
  const up=M.simulate(rows(i=>100+i),'2020-01',settings),down=M.simulate(rows(i=>3000-i),'2020-01',settings);
  assert.ok(up.lump>up.split);assert.ok(down.lump<down.split);assert.ok(down.mddL<down.mddS);
});
test('independent purchase ledger reproduces final value and total-assets drawdown',()=>{
  const source=rows(i=>100+Math.sin(i/25)*25+i/20),r=M.simulate(source,'2020-01',{...settings,months:12,years:3});
  const lookup=new Map(source.map(r=>[r[0],r[1]]));const units=r.buys.reduce((sum,b)=>sum+b.amount/lookup.get(b.day),0);
  near(r.split,units*lookup.get(r.to));near(r.lump,12000/lookup.get(r.from)*lookup.get(r.to));
  let peak=12000,dd=0;for(const p of r.curve){peak=Math.max(peak,p.split);dd=Math.min(dd,p.split/peak-1);}near(r.mddS,dd);
});
test('independent BIL lot ledger counts reinvested distributions once and clears the last lot',()=>{
  const source=rows(()=>100,i=>100+i/100+Math.sin(i/30)),r=M.simulate(source,'2020-01',settings),bil=new Map(source.map(p=>[p[0],p[2]]));
  const lot=12000/6/bil.get(r.from);
  for(const b of r.buys){near(b.principal,2000);near(b.amount,lot*bil.get(b.day));}
  for(const p of r.curve){
    const used=r.buys.filter(b=>b.day<=p.day);
    const equity=used.reduce((n,b)=>n+b.amount,0),remaining=(6-used.length)*lot*bil.get(p.day);
    near(p.reserve,remaining);near(p.split,equity+remaining);
  }
  near(r.reserve,0);near(r.split,r.buys.reduce((n,b)=>n+b.amount,0));near(r.lump,12000);
});
test('a falling BIL price transfers less money without a negative reserve or extra capital',()=>{
  const r=M.simulate(rows(()=>100,i=>3000-i),'2020-01',settings);
  assert.ok(r.buys.at(-1).amount<r.buys[0].amount);assert.ok(r.split<12000);
  near(r.buys.reduce((n,b)=>n+b.principal,0),12000);near(r.reserve,0);
  assert.ok(r.curve.every(p=>p.reserve>=0));
});
test('non-trading month starts and horizon anniversaries use the next stored session',()=>{
  const r=M.simulate(rows(),'2020-02',settings);
  assert.equal(r.from,'2020-02-03');assert.equal(r.to,'2021-02-03');
  assert.deepEqual(r.buys.map(b=>b.day),['2020-02-03','2020-03-02','2020-04-01','2020-05-01','2020-06-01','2020-07-01']);
  assert.equal(M.addMonths('2020-02-29',12),'2021-02-28');
});
test('unfinished horizons, pre-listing months and invalid input cannot produce a result',()=>{
  const source=rows();for(const month of ['1993-01','2025-12'])assert.throws(()=>M.simulate(source,month,settings),/range/);
  for(const change of [{amount:NaN},{amount:-1},{months:7},{years:2}])assert.throws(()=>M.simulate(source,'2020-01',{...settings,...change}),/inputs/);
  assert.throws(()=>M.simulate(source.map(r=>r.slice(0,2)),'2020-01',settings),/data/);
});
test('weekly, raw, mismatched, invalid and holed data are rejected',()=>{
  const d={version:2,basis:'dividend-adjusted',frequency:'daily',series:{spx:{ticker:'SPY',series:rows()}}};assert.ok(M.series(d,'spx').length);
  for(const change of [{frequency:'weekly'},{basis:'close'},{version:1}])assert.throws(()=>M.series({...d,...change},'spx'),/data/);
  for(const bad of [[['2020-02-30',100]], [['2020-01-01',100],['2020-01-02',null]], [['2020-01-01',100],['2020-02-01',100]], [['2020-01-01',100],['2020-01-01',100]]])assert.throws(()=>M.series({...d,series:{spx:{ticker:'SPY',series:bad}}},'spx'),/data/);
});
test('pairing requires exact BIL dates and begins at the shared history without padding',()=>{
  const stock=rows().map(r=>r.slice(0,2)),bil=stock.slice(200),data={version:2,basis:'dividend-adjusted',frequency:'daily',series:{spx:{ticker:'SPY',series:stock},reserve:{ticker:'BIL',series:bil}}};
  const paired=M.paired(data,'spx');assert.equal(paired[0][0],bil[0][0]);assert.equal(paired.at(-1)[0],bil.at(-1)[0]);
  assert.throws(()=>M.simulate(paired,'2018-01',settings),/range/);
  data.series.reserve.series=bil.filter((_,i)=>i!==500);assert.throws(()=>M.paired(data,'spx'),/data/);
});
test('cohorts start once per month, include only completed horizons, and account for ties',()=>{
  const source=rows(),all=M.cohorts(source,settings);assert.equal(all.length,84);
  assert.equal(all[0].month,'2018-01');assert.equal(all.at(-1).month,'2024-12');
  const summary=M.summarize(all);assert.equal(summary.ties,summary.n);assert.equal(summary.lump,0);assert.equal(summary.split,0);
});
test('changing the amount scales assets, without changing returns or drawdowns',()=>{
  const source=rows(i=>100+i/2),a=M.simulate(source,'2020-01',settings),b=M.simulate(source,'2020-01',{...settings,amount:24000});
  near(b.lump,a.lump*2);near(b.split,a.split*2);near(a.mddS,b.mddS);near(a.returnS,b.returnS);
});
test('phase-in drawdowns stop on the final scheduled purchase, not the horizon end',()=>{
  const source=rows((i,d)=>d.toISOString().slice(0,10)<'2020-08-01'?100+Math.sin(i/10)*5:20),r=M.simulate(source,'2020-01',settings);
  assert.equal(r.phase.to,r.buys.at(-1).day);
  const phase=r.curve.filter(p=>p.day<=r.phase.to);
  for(const [key,metric] of [['lump','mddL'],['split','mddS']]){
    let peak=settings.amount,drop=0;for(const p of phase){peak=Math.max(peak,p[key]);drop=Math.min(drop,p[key]/peak-1);}
    near(r.phase[metric],drop);assert.ok(r[metric]<drop);
  }
});
test('completed starting-month bounds contract when the horizon increases',()=>{
  const source=rows(),short=M.cohorts(source,{...settings,years:1}),long=M.cohorts(source,{...settings,years:5});
  assert.equal(short[0].month,long[0].month);assert.ok(long.at(-1).month<short.at(-1).month);
  assert.doesNotThrow(()=>M.simulate(source,long.at(-1).month,{...settings,years:5}));
  assert.throws(()=>M.simulate(source,short.at(-1).month,{...settings,years:5}),/range/);
});
test('both real daily histories support all settings; ledger matches independently',()=>{
  const data=JSON.parse(fs.readFileSync(path.join(root,'data/samuel/prices.json'),'utf8'));
  for(const key of ['spx','ndx'])for(const months of [3,6,12])for(const years of [1,3,5,10]){
    const source=M.paired(data,key),r=M.simulate(source,'2008-01',{amount:10000,months,years}),lookup=new Map(source.map(p=>[p[0],p[1]])),bil=new Map(source.map(p=>[p[0],p[2]]));
    const expected=r.buys.reduce((sum,b)=>sum+(10000/months*bil.get(b.day)/bil.get(r.from))/lookup.get(b.day),0)*lookup.get(r.to);
    near(r.split,expected);assert.ok(Number.isFinite(r.mddS));assert.ok(r.curve.every(p=>Number.isFinite(p.lump)&&Number.isFinite(p.split)));
    near(r.reserve,0);assert.throws(()=>M.simulate(source,'2000-01',{amount:10000,months,years}),/range/);
  }
});
test('Samuel is linked from home and sitemap with static bilingual story and shared picker',()=>{
  const html=fs.readFileSync(path.join(root,'samuel/index.html'),'utf8'),home=fs.readFileSync(path.join(root,'index.html'),'utf8'),sitemap=fs.readFileSync(path.join(root,'sitemap.xml'),'utf8');
  assert.match(home,/data-route="\/samuel\/"/);assert.match(html,/사무엘의 결정/);assert.match(html,/Samuel’s decision/);
  assert.match(html,/이미|목돈이 준비/);assert.match(html,/not a comparison of investing new monthly income/);
  for(const suffix of ['', '?lang=en','?lang=ko'])assert.ok(sitemap.includes(`<loc>https://itpaidoff.com/samuel/${suffix}</loc>`));
  assert.match(html,/shared\/language-picker.js/);assert.match(html,/hreflang="x-default"/);assert.doesNotMatch(html,/<meta name="keywords"/);
  assert.doesNotMatch(html,/id="rate"/);assert.match(html,/BIL · 미국 초단기 국채 ETF/);assert.match(html,/분배금은 재투자/);
});
