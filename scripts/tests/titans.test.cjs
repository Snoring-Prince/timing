// node --test scripts/tests/titans.test.cjs
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'titans/berkshire/index.html'), 'utf8');
let code = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).join('\n');
code = code.slice(0, code.indexOf('document.getElementById("langtabs").addEventListener'));

function page(data) {
  const ctx = {window:{}, console, data, document:{}, navigator:{languages:['ko-KR']},
    localStorage:{getItem:()=>null}, location:{search:''}, URLSearchParams};
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  vm.runInContext('RAW=data; LANG="ko"; L10N=D.ko; LOCALE="ko-KR";', ctx);
  return source => vm.runInContext(source, ctx);
}
function book(points) {
  return {quarters:points.map(([period, shares, price])=>({period, holdings:shares?
    [{cusip:'123456789', class:'COM', name:'FIXTURE', shares, value:shares*price}]:[]}))};
}
const stored = JSON.parse(fs.readFileSync(path.join(root, 'data/titans/berkshire.json'), 'utf8'));
// 검산한 분기를 기준으로 고정해, 매주 자동으로 추가되는 새 분기가 검사를 깨지 않게 합니다.
const real = {...stored, quarters:stored.quarters.filter(q=>q.period<='2026-06-30')};

test('real snapshot: totals and known Apple estimate stay intact', () => {
  const run = page(real);
  assert.equal(run('build().tc'), 299253556246);
  assert.equal(run('build().list.length'), 26);
  assert.ok(Math.abs(run('build().list.find(r=>r.key==="037833").avgCost')-39.59171393884013)<1e-9);
});
test('new and re-entered rows are not labelled held in either language', () => {
  const run = page(real);
  assert.match(run('rowHTML(build().list.find(r=>r.isNew),26,100)'), /class="act">재진입/);
  run('LANG="en";L10N=D.en;');
  assert.match(run('rowHTML(build().list.find(r=>r.isNew),26,100)'), /class="act">Back in/);
  const fresh = page(book([['2026-03-31',0,0],['2026-06-30',10,50]]));
  assert.match(fresh('rowHTML(build().list[0],1,100)'), /class="act">신규/);
});
test('periods cover exactly 1, 5, 10 and 15 years with boundary snapshots', () => {
  const run = page(real); run('build();');
  for(const [range,start] of [[4,'2025-06-30'],[20,'2021-06-30'],[40,'2016-06-30'],[60,'2011-06-30']]){
    assert.equal(run(`LRANGE=${range};QS[winStart()]`), start);
  }
});
test('split alone creates neither purchase nor return', () => {
  const run = page(book([['2026-03-31',100,100],['2026-06-30',200,50]]));
  assert.equal(run('build().list[0].dn'),0);
  assert.equal(run('build().list[0].netUSD'),0);
  assert.equal(run('tallyOf(build()).hold'),1);
  assert.equal(run('build().list[0].life.at(-1).dn'),0);
});
test('split with additional buying prices both endpoints in the same units', () => {
  const run = page(book([['2026-03-31',100,100],['2026-06-30',220,50]]));
  assert.equal(run('build().list[0].avgCost'),50);
  assert.equal(run('build().list[0].dn'),20);
});
test('full exit is recorded once without a price and re-entry resets cost', () => {
  const run=page(book([['2025-09-30',100,50],['2025-12-31',0,0],
    ['2026-03-31',0,0],['2026-06-30',20,80]]));
  assert.equal(run('build().list[0].life.filter(o=>o.exit).length'),1);
  assert.equal(run('build().list[0].life.find(o=>o.exit).p'),null);
  assert.equal(run('build().list[0].life.find(o=>o.exit).dn'),-100);
  assert.equal(run('build().list[0].avgCost'),80);
  const svg=run('chartBody(build().list[0],0).svg');
  assert.match(svg,/class="bDn"/);
  assert.equal((svg.match(/M[\d.]+ /g)||[]).length,2);
  assert.doesNotMatch(svg,/NaN|Infinity/);
});
test('prior trade counts include full exits; boundary trades stay outside the window', () => {
  const run=page(real);run('const B=build();LRANGE=60;');
  assert.match(run('chartBody(B.list.find(r=>r.key==="060505"),0).prior'),/매도 <em class="down">2<\/em>건/);
  run('LRANGE=4;');
  run('chartBody(B.list.find(r=>r.key==="037833"),0);');
  assert.equal(run('LIFES[0].pts.find(o=>o.q===QS[winStart()]).mv'),0);
});
test('all real holdings and periods render without invented zero-price exits', () => {
  const run=page(real);run('const B=build();');
  for(const range of [4,20,40,60]) for(let i=0;i<26;i++){
    assert.doesNotMatch(run(`LRANGE=${range};chartBody(B.list[${i}],${i}).svg`),/NaN|Infinity/);
  }
  assert.equal(run('B.list.find(r=>r.key==="674599").life.find(o=>o.exit).q'),'2020-06-30');
  assert.equal(run('B.list.find(r=>r.key==="674599").life.find(o=>o.exit).p'),null);
});

test('buy and sale bars rise from one baseline and cover their whole quarter', () => {
  const run=page(real);run('const B=build();LRANGE=4;LIFEW=320;');
  const svg=run('chartBody(B.list.find(r=>r.key==="037833"),0).svg');
  const bars=[...svg.matchAll(/<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" data-quarter="([^"]+)" data-shares="([\d]+)" class="(bUp|bDn)"/g)];
  assert.equal(bars.length,2);
  for(const bar of bars){
    assert.equal(bar[7],'bDn');
    assert.equal(+bar[3],74); // 300px의 시간축 / 네 분기, 경계의 1px만 띄웁니다.
    assert.ok(+bar[4]>0 && +bar[4]<=27);
  }
  assert.ok(Math.abs((+bars[0][2]+ +bars[0][4])-(+bars[1][2]+ +bars[1][4]))<.02);
  assert.equal(bars[0][5],'2025-09-30');
  assert.equal(bars[0][6],'41787236');
  assert.doesNotMatch(run('chartHTML(B.list[0])'),/lifesum|분기별 주식수 변화/);
});

test('an independent price series covers unheld periods without changing cost or trades', () => {
  const run=page(book([['2025-03-31',0,0],['2025-06-30',10,100],
    ['2025-09-30',0,0],['2025-12-31',10,150]]));
  run('const B=build();const before=B.list[0].avgCost;');
  run(`acceptPrices({method:'split-adjusted-close',series:{'123456':{ticker:'SAMPLE',currency:'USD',values:[
    ['2025-03-31',50],['2025-06-30',105],['2025-09-30',115],['2025-10-01',120],['2025-12-31',160]
  ]}}});chartBody(B.list[0],0);`);
  assert.equal(run('LIFES[0].pricePts.length'),5);
  assert.equal(run('LIFES[0].pricePts[0].q'),'2025-03-31');
  assert.equal(run('LIFES[0].pricePts.find(o=>o.q==="2025-10-01").p'),120);
  assert.equal(run('LIFES[0].pts.find(o=>o.q==="2025-09-30").mv'),-10);
  assert.equal(run('LIFES[0].daily'),true);
  assert.equal(run('build().list[0].avgCost'),run('before'));
});

test('price ingestion rejects invalid dates, zero prices and other currencies', () => {
  const run=page(real);
  run(`acceptPrices({method:'split-adjusted-close',series:{'SAMPLE':{ticker:'X',currency:'USD',values:[
    ['2026-02-31',100],['2026-06-29',0],['2026-06-30',-2],['2026-06-30',10],['2026-06-30',11]
  ]},'EUR':{ticker:'E',currency:'EUR',values:[['2026-06-30',99]]}}});`);
  assert.equal(run('PRICE_SERIES.SAMPLE.values.length'),1);
  assert.equal(run('PRICE_SERIES.SAMPLE.values[0][1]'),11);
  assert.equal(run('PRICE_SERIES.EUR'),undefined);
});

test('stored daily prices cover all current share classes and extend before investor entry', () => {
  const prices=JSON.parse(fs.readFileSync(path.join(root,'data/titans/prices.json'),'utf8'));
  const run=page(real);run('const B=build();const before=B.list.find(r=>r.key==="037833").avgCost;');
  run('acceptPrices('+JSON.stringify(prices)+');');
  assert.equal(run('B.list.filter(r=>!PRICE_SERIES[r.cusip]).length'),0);
  run('LRANGE=60;chartBody(B.list.find(r=>r.key==="037833"),0);');
  assert.ok(run('LIFES[0].pricePts[0].q')<run('B.list.find(r=>r.key==="037833").life[0].q'));
  assert.ok(run('LIFES[0].pricePts.at(-1).q')>'2026-06-30');
  assert.equal(run('build().list.find(r=>r.key==="037833").avgCost'),run('before'));
  run('chartBody(B.list.find(r=>r.key==="02079K"),1);');
  assert.equal(run('LIFES[1].ticker'),prices.series[run('B.list.find(r=>r.key==="02079K").cusip')].ticker);
  assert.notEqual(prices.series['02079K107'].ticker,prices.series['02079K305'].ticker);
  assert.notEqual(prices.series['526057104'].ticker,prices.series['526057302'].ticker);
});

test('daily chart periods follow the latest market date and trades keep calendar-quarter widths', () => {
  const run=page(real);run("acceptPrices({method:'split-adjusted-close',series:{'037833100':{ticker:'AAPL',currency:'USD',values:[['2025-09-17',200],['2026-09-17',300]]}}});const B=build();LIFEW=320;LRANGE=4;");
  assert.equal(run('chartWindow().start'),'2025-09-17');
  assert.equal(run('chartWindow().end'),'2026-09-17');
  const svg=run('chartBody(B.list.find(r=>r.key==="037833"),0).svg');
  const bar=[...svg.matchAll(/<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" data-quarter="([^"]+)"/g)];
  const partial=bar.find(m=>m[5]==='2025-09-30');
  const complete=bar.find(m=>m[5]==='2025-12-31');
  assert.ok(Math.abs(+partial[3]-(300*13/365-1))<.02);
  assert.ok(Math.abs(+complete[3]-(300*92/365-1))<.02);
  assert.doesNotMatch(svg,/data-quarter="2026-09-30"/);
  assert.match(svg,/2025\.09\.17/);assert.match(svg,/2026\.09\.17/);
  run("PRICE_ASOF='2024-02-29';LRANGE=4;");
  assert.equal(run('chartWindow().start'),'2023-02-28');
});

test('largest sale includes full exits valued at the previous snapshot', () => {
  const run=page(real);
  const state={list:[{name:'TRIM',netUSD:-500}],out:[{name:'FULL EXIT',netUSD:-1000}]};
  // 가격·수량의 곱은 실제 매도 대금이 아닙니다. 기준과 비교 결과를 두 언어에서 확인합니다.
  run(`const saleState=${JSON.stringify(state)};`);
  assert.match(run('says(saleState,{}).join("")'), /Full Exit/);
  assert.doesNotMatch(run('says(saleState,{}).join("")'), /Trim/);
  assert.match(run('tx("tradeBasis")'), /직전/);
  run('LANG="en";L10N=D.en;');
  assert.match(run('says(saleState,{}).join("")'), /Full Exit/);
  assert.match(run('tx("tradeBasis")'), /previous quarter-end/);
  const exit=page(book([['2026-03-31',10,100],['2026-06-30',0,0]]));
  assert.equal(exit('build().out[0].netUSD'), -1000);
  assert.match(exit('says(build(),{}).join("")'), /Fixture/);
});

test('positive tiny weights are not shown as zero and ordinary weights stay rounded', () => {
  const run=page(real);
  assert.equal(run('weightPct(0.00001)'), '<0.1%');
  assert.equal(run('weightPct(0.0999)'), '<0.1%');
  assert.equal(run('weightPct(0.1)'), '0.1%');
  assert.equal(run('weightPct(22.03)'), '22.0%');
  assert.equal(run('weightPct(0)'), '0.0%');
  assert.match(run('rowHTML(build().list.at(-1),26,100)'), /class="wt">&lt;0.1%/);
});

test('a new quarter updates holdings, exits, share changes and chart endpoint', () => {
  const holding=(cusip,shares,price,name)=>({cusip,shares,value:shares*price,name,class:'COM'});
  const data={quarters:[
    {period:'2026-03-31',holdings:[holding('123456789',100,10,'OLD'),holding('234567890',20,10,'KEPT')]},
    {period:'2026-06-30',holdings:[holding('123456789',60,10,'OLD'),holding('234567890',20,10,'KEPT')]}
  ]};
  const before=page(data);
  assert.equal(before('build().cur.period'),'2026-06-30');
  data.quarters.push({period:'2026-09-30',filed:'2026-11-12',holdings:[
    holding('234567890',40,12,'KEPT'),holding('345678901',10,20,'NEW')
  ]});
  const after=page(data);after('const B=build();');
  assert.equal(after('B.cur.period'),'2026-09-30');
  assert.equal(after('B.cur.filed'),'2026-11-12');
  assert.equal(after('B.tc'),680);
  assert.equal(after('B.list.length'),2);
  assert.equal(after('B.out[0].name'),'OLD');
  assert.equal(after('B.list.find(r=>r.name==="KEPT").dn'),20);
  assert.equal(after('B.list.find(r=>r.name==="NEW").isNew'),true);
  assert.equal(after('B.list.find(r=>r.name==="KEPT").life.at(-1).q'),'2026-09-30');
  assert.deepEqual(JSON.parse(after('JSON.stringify(tallyOf(B))')), {nw:1,add:1,trim:0,hold:0,out:1});
});

test('shared text follows investor settings and canonical stays stable across languages', () => {
  const run=page(real);
  run('TT.slug="sample";TT.name={en:"Example Capital",ko:"샘플 투자사"};TT.since=2020;');
  assert.match(run('tx("tagline",tName())'),/샘플 투자사/);
  assert.match(run('tx("intro",tName())'),/샘플 투자사/);
  assert.doesNotMatch(run('tx("intro",tName())'),/버크셔/);
  run('const tags={};document.head={querySelector:sel=>({setAttribute:(attr,val)=>tags[sel+attr]=val})};');
  for(const lang of ['ko','en']){
    run(`LANG="${lang}";L10N=D[LANG];location.search="?lang=${lang}";paintHead();`);
    assert.equal(run('tags[\'link[rel="canonical"]href\']'),'https://itpaidoff.com/titans/sample/');
  }
  assert.match(run('tx("intro",tName())'),/Example Capital/);
});

test('static intro provides the same explanation before JavaScript runs', () => {
  const run=page(real);run('LANG="en";L10N=D.en;');
  const intro=html.match(/<p class="intro" id="intro">([^<]+)<\/p>/)[1];
  assert.equal(intro,run('tx("intro",tName())'));
  assert.equal(html.match(/<h1 id="tagline">([^<]+)<\/h1>/)[1],run('tx("tagline",tName())'));
});
