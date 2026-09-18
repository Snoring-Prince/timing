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
  assert.match(run('chartBody(B.list.find(r=>r.key==="060505"),0).prior'),/SELL 2건/);
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
