// node --test scripts/tests/titans.test.cjs
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'titans/berkshire/index.html'), 'utf8');
const shared = fs.readFileSync(path.join(root, 'titans/shared/investor.js'), 'utf8');
const sharedCore = shared.slice(0, shared.indexOf('document.getElementById("langtabs").addEventListener'));
let code = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).join('\n')+'\n'+shared;
code = code.slice(0, code.indexOf('document.getElementById("langtabs").addEventListener'));

function page(data,titan=null) {
  const ctx = {window:titan?{TITAN:titan}:{}, console, data, document:{}, navigator:{languages:['ko-KR']},
    localStorage:{getItem:()=>null}, location:{search:''}, URLSearchParams};
  vm.createContext(ctx);
  vm.runInContext(titan?sharedCore:code, ctx);
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
  assert.match(run('rowHTML(build().list.find(r=>r.isNew),26,100)'), /class="act">Re-entered/);
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
  assert.match(run('taglineHTML()'),/샘플 투자사/);
  assert.doesNotMatch(run('taglineHTML()'),/버크셔/);
  run('const tags={};document.head={querySelector:sel=>({setAttribute:(attr,val)=>tags[sel+attr]=val})};');
  for(const lang of ['ko','en']){
    run(`LANG="${lang}";L10N=D[LANG];location.search="?lang=${lang}";paintHead();`);
    assert.equal(run('tags[\'link[rel="canonical"]href\']'),'https://itpaidoff.com/titans/sample/');
  }
  assert.match(run('taglineHTML()'),/Example Capital/);
});

test('all investor visuals and calculations come from the shared assets', () => {
  assert.match(html,/href="\.\.\/shared\/investor\.css"/);
  assert.match(html,/src="\.\.\/shared\/investor\.js"/);
  assert.doesNotMatch(html,/<style>|function build\(|function chartBody\(/);
  assert.match(shared,/function build\(/);
  assert.match(shared,/function chartBody\(/);
  assert.doesNotMatch(shared,/Berkshire Hathaway|버크셔 해서웨이|berkshire\.json/);
  const run=page(real,{slug:'sample',cik:'123',data:'sample.json',
    name:{en:'Example Capital',ko:'샘플 투자사'},since:2020,prices:'prices.json'});
  assert.equal(run('TT.slug'),'sample');
  assert.match(run('tx("tagline",tName())'),/샘플 투자사/);
  assert.equal(run('build().list.length'),26);
});

test('the static headline is byte-identical to what JavaScript paints', () => {
  const run=page(real);run('LANG="en";L10N=D.en;');
  // 크롤러가 받는 글자와 방문자가 보는 글자가 갈라지면 안 된다. 이름표·이름
  // 강조까지 같은 마크업이어야 하므로 통째로 비교한다.
  assert.equal(html.match(/<h1 id="tagline">([\s\S]*?)<\/h1>/)[1],run('taglineHTML()'));
});

test('the headline mark falls back to initials and never leaves the repository', () => {
  const run=page(real,{slug:'sample',cik:'123',data:'sample.json',
    name:{en:'Example Capital',ko:'샘플 투자사'},since:2020,prices:'prices.json'});
  // 설정이 비어 있으면 **영어 이름의 머리글자**다. 언어를 바꿔도 같아야 한다 —
  // 같은 투자자의 같은 표식이고, monogram() 은 A-Z 만 본다.
  assert.match(run('titanMark()'),/>EC</);
  run('LANG="ko";L10N=D.ko;');
  assert.match(run('titanMark()'),/>EC</);
  assert.doesNotMatch(run('titanMark()'),/https?:/);
  // 경로를 적으면 그림을 쓰되, 못 받으면 같은 타일로 떨어진다.
  run('TT.mark="logo.png";');
  assert.match(run('titanMark()'),/<img src="logo\.png"/);
  assert.match(run('titanMark()'),/onerror=/);
});

test('the quarter heading spells out the span it was computed from', () => {
  const run=page(real);
  // **손으로 적지 않습니다.** 끝날은 공시가 적은 그 날짜이고, 첫날만 분기에서
  // 셉니다 — 새 분기가 들어오면 제목이 저절로 따라옵니다.
  run('LANG="ko";L10N=D.ko;');
  assert.equal(run('tx("quarterHead","2026-06-30")'),
    '2026년 2분기 (2026. 04. 01 ~ 2026. 06. 30)');
  assert.equal(run('tx("quarterHead","2019-03-31")'),
    '2019년 1분기 (2019. 01. 01 ~ 2019. 03. 31)');
  run('LANG="en";L10N=D.en;');
  assert.equal(run('tx("quarterHead","2026-06-30")'),'Q2 2026 (Apr 1 – Jun 30, 2026)');
  assert.equal(run('tx("quarterHead","2020-12-31")'),'Q4 2020 (Oct 1 – Dec 31, 2020)');
  // 제목은 늘 실제 마지막 분기에서 나온다.
  assert.equal(run('tx("quarterHead",build().cur.period)'),'Q2 2026 (Apr 1 – Jun 30, 2026)');
});

test('the fold label says what the next click will do', () => {
  const run=page(real);
  run('LANG="ko";L10N=D.ko;');
  assert.equal(run('tx("foldOpen",16)'),'16개 종목 더 보기');
  assert.equal(run('tx("foldClose",16)'),'16개 종목 숨기기');
  run('LANG="en";L10N=D.en;');
  assert.equal(run('tx("foldOpen",16)'),'Show 16 more');
  assert.equal(run('tx("foldClose",16)'),'Hide 16');
});

test('the record lists only quarters that moved, newest first', () => {
  const run=page(real);run('LANG="ko";L10N=D.ko;');
  // 코카콜라는 111분기를 들고 있지만 분할 보정을 하면 주식수가 한 번도 안 바뀐다.
  // 다 적으면 같은 숫자가 110줄 되풀이되므로 **움직인 분기만** 싣는다.
  const ko=run('recordHTML(build().list.find(r=>r.key==="191216"))');
  assert.equal((ko.match(/<tr><td/g)||[]).length,1);
  assert.match(ko,/집계 전부터 보유/);
  // 첫 공시에 이미 있던 종목에 '진입' 이라고 적으면 그 분기에 샀다는 거짓말이 된다.
  assert.doesNotMatch(ko,/>진입</);
  const ap=run('recordHTML(build().list.find(r=>r.key==="037833"))');
  const dates=[...ap.matchAll(/class="rcq">([\d.]+)</g)].map(m=>m[1]);
  assert.equal(dates.length,26);
  assert.deepEqual(dates,[...dates].sort().reverse());   // 최신이 맨 위
  assert.equal(dates.at(-1),'2016.03.31');
  assert.match(ap,/class="rcq">2016\.03\.31<\/td><td class="rcm">진입/);
});

test('a full exit is recorded without inventing a sale price', () => {
  const run=page(real);run('LANG="ko";L10N=D.ko;');
  // 옥시덴탈은 2020 년에 전량 매도하고 2022 년에 다시 샀다. 다음 공시는 수량이
  // 사라졌다는 것만 알려 주므로 가격·금액 칸은 비운다(9-3-1 의 규칙과 같은 자리).
  const h=run('recordHTML(build().list.find(r=>r.key==="674599"))');
  const out=h.match(/<tr><td class="rcq">([\d.]+)<\/td><td class="rcm down">전량매도<\/td>(.*?)<\/tr>/);
  assert.ok(out,'전량매도 줄이 있어야 한다');
  assert.equal(out[1],'2020.06.30');
  assert.equal((out[2].match(/—/g)||[]).length,3);   // 보유·가격·금액 셋 다 비움
  assert.match(h,/class="rcm">재진입/);
  run('LANG="en";L10N=D.en;');
  assert.match(run('recordHTML(build().list.find(r=>r.key==="674599"))'),/class="rcm down">Exited/);
});

test('the record ignores the period buttons and never says "trade"', () => {
  const run=page(real);run('LANG="ko";L10N=D.ko;const R=build().list.find(r=>r.key==="037833");');
  // 차트는 고른 창을 보여 주고 이 표는 전부다. 기간을 바꿔도 줄 수가 같아야 한다.
  const n=()=>(run('recordHTML(R)').match(/<tr><td/g)||[]).length;
  run('LRANGE=4;'); const one=n();
  run('LRANGE=60;'); assert.equal(n(),one);
  // 13F 는 분기말 스냅샷뿐이라 한 줄은 체결이 아니라 그 분기의 순변화다.
  assert.doesNotMatch(run('tx("recShow")+tx("recHide")'),/거래/);
  run('LANG="en";L10N=D.en;');
  assert.doesNotMatch(run('tx("recShow")+tx("recHide")'),/trade/i);
});

test('the toggle says what the next click does, and the caret is a real triangle', () => {
  const run=page(real);run('LANG="ko";L10N=D.ko;');
  const h=run('recordHTML(build().list.find(r=>r.key==="037833"))');
  // 두 이름표가 다 들어 있고 CSS 가 여닫이에 따라 하나만 보여 준다.
  assert.match(h,/class="recbtn">분기별 보유 변화 보기</);
  assert.match(h,/class="recbtn open">분기별 보유 변화 숨기기</);
  // 건수는 단추 밖이다 — 누르기 전에 분량을 알려 주는 값이지 단추 이름이 아니다.
  assert.match(h,/class="reccnt">26개 분기</);
  // 아래 설명 줄은 유의사항과 겹쳐서 지웠다.
  assert.doesNotMatch(h,/recnote/);
  // **CSS 이스케이프가 파이썬 8진수로 먹혀 `B8`·`BE` 가 찍힌 적이 있다.**
  // 캐럿은 진짜 삼각형이어야 하고, 그 자리에 제어문자가 있으면 안 된다.
  const css=fs.readFileSync(path.join(root,'titans/shared/investor.css'),'utf8');
  assert.match(css,/\.recbtn::before\{content:"\\25B8"/);
  assert.match(css,/details\.rec\[open\] \.recbtn::before\{content:"\\25BE"\}/);
  assert.doesNotMatch(css,/[\x00-\x08\x0b-\x1f]/);
});

test('event rows can show the same mark and sector as the list', () => {
  const run=page(real);run('LANG="ko";L10N=D.ko;');
  // **전량매도 줄이 걱정거리였다** — 그 종목은 이번 분기 목록에 없다.
  // 마크는 CUSIP 으로, 섹터는 앞 여섯 자리로 찾으므로 둘 다 살아 있어야 한다.
  run('const O=build().out[0];');
  assert.ok(run('O&&O.cusip'),'전량매도 줄에 CUSIP 이 있어야 한다');
  assert.ok(run('O.key'),'전량매도 줄에 섹터 열쇠가 있어야 한다');
  assert.match(run('markHTML(O)'),/class="mk/);
  run('const I=build().list.find(r=>r.isNew);');
  assert.match(run('markHTML(I)'),/class="mk/);
  // 검사에서는 섹터 표를 안 읽으므로(화면만 받는다) 표를 끼워 길이 확인한다.
  // 실제 값은 브라우저에서 쟀다 — 음료 · 주택건설.
  run('SECTORS={[O.key]:{sic:"2084"},[I.key]:{sic:"1531"}};');
  assert.ok(run('sectorOf(O)').length>0,'전량매도 줄도 섹터가 나와야 한다');
  assert.ok(run('sectorOf(I)').length>0);
  run('SECTORS={};');
  assert.equal(run('sectorOf(O)'),'','모르면 비운다 — 틀린 것을 적지 않는다');
  // 마크를 못 찾아도 화면은 돈다 — 목록과 똑같이 글자 타일로 떨어진다.
  run('TICKERS={};');
  assert.match(run('markHTML({cusip:"G1234567",key:"G12345",name:"Example Ltd"})'),/class="mk/);
});

test('the investor blurb is prose in the page, not strings in the shared screen', () => {
  const css=fs.readFileSync(path.join(root,'titans/shared/investor.css'),'utf8');
  // 사전에 넣으면 JS 가 그리게 되고, JS 를 안 돌리는 크롤러가 받는 페이지에서
  // 통째로 사라진다(본 사이트의 `.about` 과 같은 자리 — CLAUDE.md 6-2).
  assert.doesNotMatch(shared,/Warren Buffett|워런 버핏|holding period is forever/);
  assert.doesNotMatch(css,/Warren Buffett|워런 버핏/);
  const bio=html.match(/<section class="panel bio" id="titan-bio">([\s\S]*?)<\/section>/)[1];
  assert.match(bio,/data-lang="en"/); assert.match(bio,/data-lang="ko"/);
  // 두 언어가 같은 조각 수를 가져야 한쪽만 고치는 실수가 드러난다.
  const count=lg=>bio.match(new RegExp(`data-lang="${lg}"`,'g')).length;
  assert.equal(count('en'),count('ko'));
  // 인용은 출처 없이 싣지 않는다.
  const quotes=bio.match(/<blockquote[\s\S]*?<\/blockquote>/g);
  assert.equal(quotes.length,4);
  for(const q of quotes) assert.match(q,/<cite>[^<]+<\/cite>/);
  // 화면에 보이는 쪽은 CSS 가 고른다 — 한쪽 언어만 보여야 한다.
  assert.match(css,/html\[lang="ko"\][^{]*\.bio \[data-lang="en"\]\{display:none\}/);
  assert.match(css,/html:not\(\[lang="ko"\]\)[^{]*\.bio \[data-lang="ko"\]\{display:none\}/);
  // 그림이 없으면 그림 칸만 빠지고 깨진 그림이 안 남는다.
  assert.match(bio,/onerror="this\.closest\('\.bio'\)\.classList\.add\('nofigure'\)/);
  assert.match(css,/\.bio\.nofigure\{grid-template-columns:minmax\(0,1fr\)\}/);
  // 공통 JS 는 이 덩어리를 머리글 아래 제자리로 옮길 뿐이다.
  assert.match(shared,/getElementById\("titan-bio"\)/);
  assert.match(shared,/insertBefore\(bio,q\)/);
});

test('english counts say "1 quarter", not "1 quarters"', () => {
  const run = page(real);
  run('LANG="en";L10N=D.en;');
  assert.equal(run('tx("recCount",1)'), '1 quarter');
  assert.equal(run('tx("recCount",2)'), '2 quarters');
  assert.equal(run('tx("positions",1)'), '1 position');
  assert.equal(run('tx("positions",26)'), '26 positions');
  assert.equal(run('tx("yr",1)'), '1 year');
  assert.equal(run('tx("yr",1.5)'), '1.5 years');
  assert.equal(run('tx("yr",0.5)'), '6 months');
  // 한국어는 수를 세지 않으므로 그대로다.
  run('LANG="ko";L10N=D.ko;');
  assert.equal(run('tx("recCount",1)'), '1개 분기');
});

test('one word never has to mean three things on the same screen', () => {
  const run = page(real);
  run('LANG="en";L10N=D.en;');
  // 열 머리글은 `Shares held`, 전량매도 줄은 `held 1.5 years` 를 쓴다. 그러니
  // "이번 분기에 안 움직였다"를 또 `held` 라고 부르면 한 낱말이 세 가지가 된다.
  assert.equal(run('tx("same")'), 'unchanged');
  assert.equal(run('tx("kHold")'), 'unchanged');
  // 같은 사건을 계기판과 사건 줄이 다른 이름으로 부르지 않는다.
  assert.equal(run('tx("evOut")'), 'Exited');
  assert.equal(run('tx("rcOut")'), 'Exited');
  assert.match(run('tx("kOut")'), /^exited$/i);
  assert.equal(run('tx("evBack")'), run('tx("rcBack")'));
  // 그 칸에 찍히는 것은 분기 마지막 날이지 공시일이 아니다.
  assert.doesNotMatch(run('tx("rcDate")'), /filing/i);
});

test('the chart labels a quarter with the same number the record shows', () => {
  for (const lang of ['ko','en']) {
    const run = page(real);
    run(`LANG="${lang}";L10N=D.${lang};LOCALE=D.${lang}.locale;`);
    // 애플 2024.06.30 은 −389,368,450 주. 차트 막대 이름표와 표의 `변화` 칸이
    // 같은 수를 두 가지로 적으면 한 줄 안에서 화면이 자기 말을 어긴다.
    assert.equal(run('compShares(389368450)'), run('shortShares(389368450)'));
    assert.equal(run('compShares(333856)'), run('shortShares(333856)'));
  }
  const ko = page(real); ko('LANG="ko";L10N=D.ko;LOCALE="ko-KR";');
  assert.equal(ko('compShares(389368450)'), '3.89억주');
  // 한글은 고정폭에서도 두 칸을 쓴다 — 글자 수로 재면 이웃과 겹친다.
  assert.ok(ko('labWidth("3.89억주")') > ko('labWidth("389.4M")'));
});

test('no dictionary entry is left behind after a feature is removed', () => {
  const a = shared.indexOf('const D={'), b = shared.indexOf('\nconst REDUP');
  const dict = shared.slice(a, b), rest = shared.slice(0, a) + shared.slice(b);
  const keys = [...new Set([...dict.matchAll(/^ {2}([a-zA-Z][a-zA-Z0-9]*)\s*:/gm)].map(m => m[1]))];
  const dead = keys.filter(k => !new RegExp('["\'.]' + k + '\\b').test(rest));
  assert.deepEqual(dead, [], '화면이 안 읽는 사전 키: ' + dead.join(', '));
  // 두 언어가 같은 열쇠를 갖는지도 같이 본다 — 한쪽만 지우는 실수가 제일 잦다.
  const run = page(real);
  assert.deepEqual(run('Object.keys(D.en).sort()'), run('Object.keys(D.ko).sort()'));
});

test('a real 3:2 split is not read as 2:1', () => {
  const run = page(real);
  // 허용차가 ±30% 인데 1.5 ÷ 2 = 0.75, 정확히 25% 차이라 진짜 3:2 가 2:1 의
  // 밴드 안으로 들어왔다. 틀린 배수로 '고치면' 33% 오차가 조용히 박힌다.
  assert.equal(run('splitFactor(1.5, 1.5)'), 1.5);
  // 퍼싱 스퀘어 브룩필드 2025Q4 — 41,020,231 → 61,403,089 주, 가격 ÷1.5
  assert.equal(run('splitFactor(61403089/41020231, 1.5)'), 1.5);
  // 2배 미만은 정확히 맞을 때만. 사람의 매매는 1.500000 에 안 떨어진다.
  assert.equal(run('splitFactor(1.552, 1.140)'), null);   // 애플 2016-06 — 55% 더 산 것
  assert.equal(run('splitFactor(1.429, 1.182)'), null);   // 레너드 2026-03
  // 동그란 숫자로 사면 비율이 정확히 1.5 다 — 가격이 거부권을 쥔다.
  assert.equal(run('splitFactor(1.5, 0.867)'), null);     // GM 2012-09, 주가가 오른 분기
  // 5:4·4:3 은 후보에 없다. 1.25 근처에서는 가격 거부권이 힘을 못 쓴다.
  assert.equal(run('splitFactor(1.2413, 1.032)'), null);  // 셰브런 2021-09
  assert.equal(run('splitFactor(1.25, 1.25)'), null);
  // 진짜 큰 분할은 그대로 잡힌다 — 애플 2020-09 는 분기 중 주가가 27% 올랐다.
  assert.equal(run('splitFactor(3.852, 3.150)'), 4);
  assert.equal(run('splitFactor(2, 2)'), 2);
});

test('the known holdings keep the estimates the split fix must not move', () => {
  const run = page(real);
  // 지금 보유 26종목은 이번 변경으로 하나도 안 움직여야 한다.
  assert.ok(Math.abs(run('build().list.find(r=>r.key==="037833").avgCost')-39.59171393884013)<1e-9);
  assert.equal(run('build().list.length'), 26);
  assert.equal(run('build().tc'), 299253556246);
  assert.equal(run('build().gap'), 1);   // 빠진 분기 없음
});

test('a missing quarter is never passed off as "this quarter"', () => {
  const full = page(real);
  const q = real.quarters.map(x=>x.period);
  const bofa = '060505';
  const trueQ2 = full(`build().list.find(r=>r.key==="${bofa}").dn`);
  // 2026Q1 을 빼면 qs[len-2] 가 두 분기 전이 된다.
  const holed = {...real, quarters: real.quarters.filter(x=>x.period!=='2026-03-31')};
  const run = page(holed);
  assert.equal(run('build().gap'), 2, '빠진 분기를 세지 못했다');
  const twoQ = run(`build().list.find(r=>r.key==="${bofa}").dn`);
  assert.notEqual(twoQ, trueQ2, '두 분기치가 한 분기치와 같을 수 없다');
  // 머리글과 안내 문구가 '이번 분기'라고 우기지 않는다.
  run('LANG="ko";L10N=D.ko;');
  assert.notEqual(run('tx("colQtrGap")'), run('tx("colQtr")'));
  assert.match(run('tx("gapNote","2025-12-31",2)'), /2025년 4분기/);
  run('LANG="en";L10N=D.en;');
  assert.match(run('tx("gapNote","2025-12-31",2)'), /Q4 2025[\s\S]*2 quarters/);
  void q;
});

test('one filing on its own does not turn every holding into a new buy', () => {
  const only = {...real, quarters: real.quarters.slice(-1)};
  const run = page(only);
  assert.equal(run('build().gap'), 0);
  assert.equal(run('build().list.filter(r=>r.isNew).length'), 0, '비교할 공시가 없는데 신규로 찍혔다');
  assert.equal(run('build().list.filter(r=>r.noPrev).length'), 26);
  // 가운데 칸은 '쓸 값이 없다'는 뜻의 줄표만 적는다.
  assert.match(run('rowHTML(build().list[0],26,100)'), /class="act">—</);
});

// 진짜 분할 기록은 `data/titans/prices.json` 에 이미 들어 있다. 화면이 그것을
// 읽게 하면 추측할 필요가 없어진다 — 단, 야후의 `splits` 는 분할 목록이 아니다.
const priceBook = JSON.parse(fs.readFileSync(path.join(root,'data/titans/prices.json'),'utf8'));
function withPrices(data){
  const run = page(data);
  run('__P=' + JSON.stringify(priceBook) + ';acceptPrices(__P);');
  return run;
}

test('a spin-off is not a split, however Yahoo files it', () => {
  const run = page(real);
  // 진짜 액면분할 — 기약분수로 줄이면 작은 정수다.
  assert.equal(run('splitRatio("2.0:1.0")'), 2);
  assert.equal(run('splitRatio("4.0:1.0")'), 4);
  assert.equal(run('splitRatio("7.0:1.0")'), 7);
  assert.equal(run('splitRatio("20.0:1.0")'), 20);
  assert.equal(run('splitRatio("3:2")'), 1.5);
  assert.equal(run('splitRatio("5:4")'), 1.25);
  assert.equal(run('splitRatio("4:3")'), 4/3);
  assert.equal(run('splitRatio("1.0:10.0")'), 0.1);       // 역분할
  // 분할이 아닌 것 — 전부 실제 저장된 값이다.
  for (const notSplit of ['1046.0:1000.0',   // 제퍼리스 2023 스핀오프
                          '1017.0:1000.0',   // 레나 2017
                          '102.0:100.0',     // 레나B 2017 → 51:50
                          '10000.0:9983.0',  // 옥시덴탈 2016
                          '310.0:1.0',       // Ally 전환
                          '2002.0:1000.0',   // 구글 C주 배분
                          '1.0:1.0', '', 'x:y', '0:1'])
    assert.equal(run(`splitRatio(${JSON.stringify(notSplit)})`), null, notSplit+' 를 분할로 받았다');
});

test('the real split record replaces the guess where the data reaches', () => {
  const run = withPrices(real);
  // 애플: 2014 년 7:1 과 2020 년 4:1 이 둘 다 실제로 적혀 있다.
  // vm 밖으로 나온 배열은 프로토타입이 달라 deepEqual 이 걸린다 — 값으로 본다.
  const days = run('JSON.stringify([...SPLIT_BOOK["037833"].days.entries()])');
  assert.equal(days, JSON.stringify([['2014-06-09',7],['2020-08-31',4]]));
  // 그 분할이 든 분기만 배수가 나오고, 없는 분기는 1 이다.
  assert.equal(run('realSplit("037833","2020-06-30","2020-09-30")'), 4);
  assert.equal(run('realSplit("037833","2021-06-30","2021-09-30")'), 1);
  // **자료가 못 미치는 옛 분기는 `undefined` 여야 한다** — 1 이라고 답하면
  // 아메리칸익스프레스 2000 년 3:1 이 통째로 사라진다.
  assert.equal(run('realSplit("025816","2000-03-31","2000-06-30")'), undefined);
  assert.equal(run('realSplit("없는키","2020-06-30","2020-09-30")'), undefined);
  // 스핀오프는 받지 않으므로 제퍼리스에는 분할이 하나도 없다.
  assert.equal(run('(SPLIT_BOOK["47233W"]||{days:new Map()}).days.size'), 0);
});

test('a deeper split scan opens the quarters the guess used to own', () => {
  // 수집기가 상장 때부터 훑으면 `splitsFrom` 이 붙고 15년 창 밖의 분할이 실려 온다.
  // 아메리칸익스프레스 2000-05-11 3:1 이 그 자리다.
  const deep = JSON.parse(JSON.stringify(priceBook));
  for (const [key, one] of Object.entries(deep.series)) {
    one.splitsFrom = '1970-01-01';
    if (key.startsWith('025816')) one.splits = {...one.splits, '2000-05-11': '3.0:1.0'};
  }
  const run = page(real);
  run('__P=' + JSON.stringify(deep) + ';acceptPrices(__P);');
  assert.equal(run('realSplit("025816","2000-03-31","2000-06-30")'), 3);
  // 분할이 없던 옛 분기는 1 이다 — 덮은 구간 안이므로 추측기로 넘기지 않는다.
  assert.equal(run('realSplit("025816","2001-03-31","2001-06-30")'), 1);
  // **표식이 없는 옛 파일은 예전 그대로** 가격 시작일까지만 덮는다.
  assert.equal(withPrices(real)('realSplit("025816","2000-03-31","2000-06-30")'), undefined);
});

test('switching to the real record does not move a single holding', () => {
  const guessed = page(real), measured = withPrices(real);
  const pick = 'JSON.stringify(build().list.map(r=>[r.key,r.avgCost,r.dn,r.shares]))';
  assert.equal(measured(pick), guessed(pick));
  // 애플은 두 길 모두 같은 값이어야 한다(분할 ×4 를 양쪽이 똑같이 잡는다).
  assert.ok(Math.abs(measured('build().list.find(r=>r.key==="037833").avgCost')-39.59171393884013)<1e-9);
});
