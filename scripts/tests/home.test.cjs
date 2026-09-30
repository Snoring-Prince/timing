// node --test scripts/tests/home.test.cjs — no network or extra packages.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {test}=require('node:test'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const script=html.match(/<script id="home-app">([\s\S]*?)<\/script>/)[1];
const helpers=script.slice(script.indexOf('  const DAY='),script.indexOf('  // Page setup:'));
const ctx=vm.createContext({});vm.runInContext(helpers,ctx);
const plain=v=>JSON.parse(JSON.stringify(v));
const model=m=>plain(ctx.previewModel(m));
const market=(prices,fear=[])=>({indices:{spx:{series:prices}},fng:{series:fear}});

test('preview uses the last observed year, rejects invalid values, and matches fear by exact date',()=>{
  const data=market([
    ['2024-08-01',90],['2025-09-30',100],['2026-09-25',110],['2026-09-28',105],
    ['2026-09-29',null],['2026-02-30',9000],['2026-09-30',0],['2026-10-01','200']
  ],[['2025-09-30',44],['2026-09-25',45],['2026-09-26',10],['2026-09-28',null]]);
  const got=model(data);
  assert.equal(got.from,'2025-09-30');assert.equal(got.to,'2026-09-28');
  assert.deepEqual(got.prices,[['2025-09-30',100],['2026-09-25',110],['2026-09-28',105]]);
  assert.deepEqual(got.fear,['2025-09-30']);
});

test('missing or malformed sources never produce an invented curve',()=>{
  for(const bad of [null,{},market([]),market([['bad',2]]),market([['2026-09-29',2]]),market({oops:1})])assert.equal(model(bad),null);
  const good=model(market([['2026-09-28',100],['2026-09-29',101]],[[null,0],['2026-09-28',-1],['2026-09-29',101]]));
  assert.deepEqual(good.fear,[]);
  assert.doesNotMatch(ctx.previewSVG(good,240).body,/class="fear"/);
});

test('a price gap breaks the line and flat prices do not create NaN coordinates',()=>{
  const gap=model(market([['2026-09-01',100],['2026-09-02',null],['2026-09-03',100],['2026-09-04',100],['2026-09-20',100]]));
  const svg=ctx.previewSVG(gap,210).body;
  const d=svg.match(/class="price" d="([^"]+)"/)[1];
  assert.equal((d.match(/M/g)||[]).length,3);
  assert.equal((d.match(/L/g)||[]).length,1);
  assert.doesNotMatch(svg,/NaN|Infinity/);
});

test('latest real visitor data renders valid prices and never carries fear past its last observation',()=>{
  const raw=JSON.parse(fs.readFileSync(path.join(root,'data/dashboard/market.json'),'utf8'));
  const got=model(raw);assert.ok(got.prices.length>10);
  const source=new Map(raw.indices.spx.series),fear=new Map(raw.fng.series);
  for(const [d,v] of got.prices)assert.equal(v,source.get(d));
  for(const d of got.fear)assert.ok(typeof fear.get(d)==='number'&&fear.get(d)<45);
  assert.doesNotMatch(ctx.previewSVG(got,220).body,/NaN|Infinity|undefined/);
});

test('each service has a closed, native story and bilingual static content before JavaScript',()=>{
  const body=html.match(/<body>([\s\S]*?)<script id="home-app">/)[1];
  const cards=[...body.matchAll(/<article\b[^>]*>([\s\S]*?)<\/article>/g)];
  assert.ok(cards.length>=2);
  const ids=new Set();
  for(const [,card] of cards){
    const details=card.match(/<details ([^>]*)>([\s\S]*?)<\/details>/);assert.ok(details);
    assert.match(details[1],/name="service-stories"/);assert.doesNotMatch(details[1],/\bopen(?:\s|=|$)/);
    const id=details[1].match(/id="([^"]+)"/)[1];assert.ok(!ids.has(id));ids.add(id);
    assert.match(details[2],/<summary>[\s\S]*?<\/summary>/);
    assert.equal((card.match(/data-lang="ko"/g)||[]).length,(card.match(/data-lang="en"/g)||[]).length);
    assert.match(card,/<a class="home-direct" href="\/(?:timing|titans)\/"/);
  }
  assert.doesNotMatch(body,/Coming|준비 중|class="s-person"|class="s-story"/);
  assert.ok(fs.statSync(path.join(root,'assets/home/titans-group.webp')).size<250000);
  assert.match(body,/alt="An imagined group portrait/);
});
