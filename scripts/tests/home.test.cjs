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

test('each service card is one link with a button, bilingual static content before JavaScript',()=>{
  const body=html.match(/<body>([\s\S]*?)<script id="home-app">/)[1];
  // 카드 한 장이 통째로 링크이고, 오른쪽 아래 따로 가는 링크·여닫는 이야기는 없습니다(2026-09-30 사용자 요청).
  const cards=[...body.matchAll(/<a class="s-service[^"]*" href="(\/(?:timing|titans)\/)" data-go="(\w+)" data-route="([^"]+)">([\s\S]*?)<\/a>\r?\n/g)];
  assert.equal(cards.length,2);
  const want={timing:['이야기 읽기','Read the story'],titans:['거장들 만나보기','Meet the investors']};
  for(const [,href,go,route,card] of cards){
    assert.equal(route,href);assert.equal(href,`/${go}/`);
    assert.doesNotMatch(card,/<a[\s>]|<button|<details/);   // 링크 안에 링크·버튼을 넣지 않습니다
    const [ko,en]=want[go];
    assert.ok(card.includes(`<span class="go"><span data-lang="ko">${ko}</span><span data-lang="en">${en}</span></span>`),go);
    assert.equal((card.match(/data-lang="ko"/g)||[]).length,(card.match(/data-lang="en"/g)||[]).length);
  }
  assert.doesNotMatch(body,/<details|home-direct|결실|Did it pay off|Coming|준비 중|class="s-person"|class="s-story"/);
  // 올리면 버튼의 글자색과 바탕색이 뒤바뀝니다.
  assert.match(html,/a\.s-service:hover \.go\{background:var\(--s-accent\);color:#fff\}/);
  assert.ok(fs.statSync(path.join(root,'assets/home/titans-group.webp')).size<250000);
  assert.match(body,/alt="An imagined group portrait/);
});
