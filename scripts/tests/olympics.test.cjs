const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const M=require('../../olympics/model.js');
function sessions(from='2025-01-02',to='2025-04-10'){const a=[];for(let d=new Date(from);d<=new Date(to);d.setUTCDate(d.getUTCDate()+1))if(d.getUTCDay()%6)a.push(d.toISOString().slice(0,10));return a;}
const hold=(key,shares,value=shares*10,cusip=key)=>({key,ticker:key,cusip,shares,value});
function fixture(){
  const days=sessions(),series=days.map(d=>[d,100]);
  return {version:1,basis:'dividend-adjusted',from:days[0],to:days.at(-1),etfs:{spx:series,ndx:structuredClone(series),reserve:structuredClone(series)},fear:days.map(d=>[d,50]),
    disclosures:[{period:'2024-09-30',filed:'2024-11-14',holdings:[hold('OLD',10)]},
      {period:'2024-12-31',filed:'2025-01-03',holdings:[hold('OLD',20),hold('AAA',40),hold('BBB',60)]}],
    stocks:Object.fromEntries(['AAA','BBB'].map(k=>[k,{ticker:k,series:days.map(d=>[d,10]),splits:{}}]))};
}
function actor(r,id){return r.trades.filter(t=>t.actor===id);}
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`);
test('five accounts share one initial budget, with no external deposits or overdraft',()=>{
  const r=M.run(fixture(),{amount:1000,monthly:10,alicia:100,buy:100,sell:100,repeat:true});
  for(const p of r.curve)for(const id of M.ids){close(p.values[id],1000);assert.ok(p.reserves[id]>=0&&p.reserves[id]<=1000);}
  assert.equal(actor(r,'john').length,0);assert.equal(actor(r,'emma').length,1);
});
test('Alicia waits for public disclosure, weights new positions and ignores grown old holdings',()=>{
  const r=M.run(fixture(),{amount:1000});
  assert.deepEqual(actor(r,'alicia').map(t=>[t.day,t.key,t.amount]),[['2025-01-06','AAA',80],['2025-01-06','BBB',120]]);
  assert.ok(actor(r,'alicia').every(t=>t.filed==='2025-01-03'&&t.signalDay<t.day));
  close(r.curve[1].reserves.alicia,1000);
});
test('amendment additions become tradable only after their later publication',()=>{
  const data=fixture();data.disclosures.push({period:'2024-12-31',filed:'2025-01-07',holdings:[hold('OLD',20),hold('AAA',60),hold('BBB',60)]});
  const r=M.run(data,{amount:1000}),trades=actor(r,'alicia');
  assert.equal(trades.at(-1).day,'2025-01-08');assert.equal(trades.at(-1).reason,'add');close(trades.at(-1).amount,200);
  assert.equal(trades.filter(t=>t.day<'2025-01-08').length,2);
});
test('Alicia proportionally reduces and fully exits, then reinvests proceeds in BIL',()=>{
  const data=fixture();data.disclosures.push({period:'2024-12-31',filed:'2025-01-07',holdings:[hold('OLD',20),hold('AAA',20),hold('BBB',60)]},
    {period:'2024-12-31',filed:'2025-01-09',holdings:[hold('OLD',20)]});
  const r=M.run(data,{amount:1000}),sales=actor(r,'alicia').filter(t=>t.action==='sell');
  assert.deepEqual(sales.map(t=>[t.day,t.key,t.amount]),[['2025-01-08','AAA',40],['2025-01-10','AAA',40],['2025-01-10','BBB',120]]);
  close(r.curve.at(-1).reserves.alicia,1000);
});
test('filings before the selected start do not buy an already disclosed portfolio',()=>{
  const r=M.run(fixture(),{start:'2025-01-07'});assert.equal(actor(r,'alicia').length,0);
});
test('stock splits and identifier changes are not false purchases',()=>{
  const data=fixture();data.disclosures.push({period:'2025-03-31',filed:'2025-04-03',holdings:[hold('OLD',20),hold('AAA',80,800,'NEWCUSIP'),hold('BBB',60)]});
  data.stocks.AAA.splits={'2025-02-03':2};const r=M.run(data);
  assert.equal(actor(r,'alicia').length,2);
});
test('Daniel acts the next session only on zone entry, including fear zero and greed boundary',()=>{
  const data=fixture(),v=[0,0,50,10,90,90,50,10];data.fear=data.fear.map(([d],i)=>[d,v[i]??50]);
  const r=M.run(data,{amount:1000});const tr=actor(r,'daniel');
  assert.deepEqual(tr.map(t=>[t.action,t.day]),[['buy','2025-01-03'],['buy','2025-01-08'],['sell','2025-01-09'],['buy','2025-01-14']]);
  assert.ok(tr.every(t=>t.signalDay<t.day));
});
test('Daniel repeat is explicit and purchases/sales stay within available money',()=>{
  const data=fixture();data.fear=data.fear.map(([d],i)=>[d,i<10?10:90]);
  const r=M.run(data,{amount:1000,repeat:true,buy:70,sell:70});
  assert.deepEqual(actor(r,'daniel').map(t=>t.amount),[700,300,700,300]);
  assert.ok(r.curve.every(p=>p.reserves.daniel>=0));
});
test('missing sentiment creates neither a signal nor a false re-entry after the gap',()=>{
  const data=fixture();data.fear=data.fear.map(([d],i)=>[d,i<2?50:0]).filter(([d])=>d!=='2025-01-03');
  const r=M.run(data);assert.equal(actor(r,'daniel').length,0);assert.equal(r.missingFear,1);
  assert.equal(actor(M.run(data,{repeat:true}),'daniel')[0].day,'2025-01-07');
});
test('Samuel uses a fixed initial-budget percentage each month and then stops at the balance',()=>{
  const data=fixture(),r=M.run(data,{amount:1000,monthly:10});
  assert.deepEqual(actor(r,'samuel').map(t=>[t.day,t.amount]),[['2025-01-02',100],['2025-02-03',100],['2025-03-03',100],['2025-04-01',100]]);
});
test('adjusted-price returns match an independent reserve/equity unit ledger and dividends are not added twice',()=>{
  const data=fixture(),ds=data.etfs.spx.map(r=>r[0]);
  data.etfs.reserve=ds.map((d,i)=>[d,100*Math.pow(1.001,i)]);data.etfs.spx=ds.map((d,i)=>[d,100+Math.sin(i/8)*15+i]);
  const r=M.run(data,{amount:1000,monthly:10}),last=r.curve.at(-1),prices=new Map(data.etfs.spx),bil=new Map(data.etfs.reserve);
  close(last.values.john,1000*bil.get(last.day)/100);close(last.values.emma,10*prices.get(last.day));
  let cashUnits=10,equityUnits=0;for(const d of ['2025-01-02','2025-02-03','2025-03-03','2025-04-01']){cashUnits-=100/bil.get(d);equityUnits+=100/prices.get(d);}
  close(last.values.samuel,cashUnits*bil.get(last.day)+equityUnits*prices.get(last.day));
});
test('drawdown and rank use the selected observation; no negative zero or invented profits',()=>{
  const data=fixture();data.etfs.spx=data.etfs.spx.map(([d],i)=>[d,i===1?200:i===2?100:100]);
  const r=M.run(data),p=r.curve[2];close(p.drops.emma,-.5);assert.equal(M.rank(r.curve[0],10000).filter(r=>r.rank===1).length,5);
  assert.equal(M.rank(r.curve[1],10000)[0].id,'emma');
});
test('missing held stock invalidates the comparison; pre-entry gaps are harmless',()=>{
  const data=fixture();data.stocks.AAA.series=data.stocks.AAA.series.filter(r=>r[0]!=='2025-01-07');
  assert.throws(()=>M.run(data),/price:AAA:2025-01-07/);
  data.stocks.AAA.series=fixture().stocks.AAA.series.filter(r=>r[0]!=='2025-01-02');assert.doesNotThrow(()=>M.run(data));
});
test('invalid dates, currencies basis, incomplete ETF calendars and unsupported decisions fail explicitly',()=>{
  assert.throws(()=>M.run(fixture(),{fear:90,greed:10}),/inputs/);assert.throws(()=>M.run(fixture(),{monthly:11}),/inputs/);
  assert.throws(()=>M.run(fixture(),{start:'2025-01-04',end:'2025-01-05'}),/range/);
  const data=fixture();data.etfs.reserve.splice(5,1);assert.throws(()=>M.prepare(data),/data/);
  assert.throws(()=>M.prepare({...fixture(),basis:'close'}),/data/);
});
test('real publication data covers both benchmarks, first-publication chronology and bounded account values',()=>{
  const data=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../data/olympics/race.json'),'utf8'));
  const prepared=M.prepare(data);
  for(const asset of ['spx','ndx'])for(const repeat of [false,true]){
    const r=M.run(prepared,{asset,repeat});for(const p of r.curve)for(const id of M.ids){assert.ok(Number.isFinite(p.values[id])&&p.reserves[id]>=0);}
    for(const t of actor(r,'alicia'))assert.ok(t.filed<t.day&&t.day>=r.from);
  }
});
test('page has static bilingual stories, five standalone strategies, methods and no fabricated preview curve',()=>{
  const html=fs.readFileSync(path.resolve(__dirname,'../../olympics/index.html'),'utf8');
  assert.equal((html.match(/strategies\//g)||[]).length,5);assert.match(html,/2025년부터/);assert.match(html,/publicly disclosed/);
  assert.match(html,/배당·분배금 재투자/);assert.match(html,/role="status"/);assert.doesNotMatch(html,/meta name="keywords"/);
});
