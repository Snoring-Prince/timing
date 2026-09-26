const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {test}=require('node:test'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const html=fs.readFileSync(path.join(root,'timing/index.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
const lang=scripts.find(s=>s.includes('const D=')||s.includes('const D =')).replace('applyLang(pickLang(),false);','');
const full=scripts.find(s=>s.includes('let DATA='));
const core=full.slice(0,full.lastIndexOf('\nloadPrefs();'));
function page(vix=false){
 const nodes=new Map(),listeners={};
 const el=()=>({innerHTML:'',textContent:'',clientWidth:818,style:{setProperty(){}},setAttribute(){},getAttribute:()=>vix?'visible':'hidden',
  querySelectorAll:()=>[],querySelector:()=>null,addEventListener(){},classList:{contains:()=>true,add(){}}});
 const node=id=>{if(!nodes.has(id))nodes.set(id,el());return nodes.get(id)};
 const timers=new Map();let seq=0;
 const ctx={console,URLSearchParams,Intl,Date,URL,AbortController,navigator:{languages:['en-US']},
  location:{search:''},localStorage:{getItem:()=>null},
  window:{LIVE:{url:'https://test.invalid'},addEventListener(){}},
  document:{getElementById:node,querySelector:()=>el(),querySelectorAll:()=>[],hidden:false,
   addEventListener:(key,fn)=>{listeners[key]=fn},body:el(),documentElement:el(),head:el()},
  setTimeout:(fn,ms)=>{timers.set(++seq,{fn,ms});return seq},clearTimeout:id=>timers.delete(id),
  fetch:async()=>{throw Error('unexpected network')},requestAnimationFrame:()=>0,
  performance:{now:()=>0}};
 vm.createContext(ctx);vm.runInContext(lang+'\n'+core,ctx);
 const run=s=>vm.runInContext(s,ctx);
 run('LANG="ko";L10N=D.ko;LOCALE="ko-KR";');
 return {run,ctx,nodes,node,timers,listeners};
}

test('hidden VIX cannot return through saved preferences or fallback controls',()=>{
 const {run,ctx,node}=page();
 ctx.localStorage.getItem=()=>JSON.stringify({ax:'vix',hold:'5Y',show:{price:'ndx',gauge:true}});
 run('loadPrefs()');assert.equal(run('btAx'),'fng');assert.equal(run('btH'),'5Y');
 run('LONG='+fs.readFileSync(path.join(root,'data/market-long.json'),'utf8')+';');
 run('BT='+fs.readFileSync(path.join(root,'data/backtest.json'),'utf8')+';');
 assert.doesNotMatch(run('mainLineSeg()'),/vix/i);assert.equal(run('btAxTools()'),'');
 run('btHover=()=>{};calibrateDraw=()=>{};btAx="vix";renderBT()');assert.equal(run('btAx'),'fng');
 assert.doesNotMatch(node('bt-title').innerHTML,/vix/i);
 for(const d of ['ko','en'])assert.doesNotMatch(run('D.'+d+'.docTitle+D.'+d+'.metaDesc+D.'+d+'.foot.join("")'),/vix/i);
});

test('feature switch restores VIX controls, stored choice and original file paths',()=>{
 const {run,ctx}=page(true);
 ctx.localStorage.getItem=()=>JSON.stringify({ax:'vix'});run('loadPrefs()');assert.equal(run('btAx'),'vix');
 run('LONG='+fs.readFileSync(path.join(root,'data/market-long.json'),'utf8')+';');
 run('BT='+fs.readFileSync(path.join(root,'data/backtest.json'),'utf8')+';');
 assert.match(run('mainLineSeg()'),/data-mline="vix"/);assert.match(run('btAxTools()'),/data-btax="vix"/);
 assert.equal(run('dashboardData("market.json")'),'../data/market.json');
});

test('hidden mode fetches only visitor JSON and requests just visible live series',async()=>{
 const {run,ctx}=page(),urls=[];
 run('renderMain=()=>{};renderBT=()=>{};calibrateDraw=()=>{};');
 ctx.fetch=async url=>{
  urls.push(url);
  return {ok:true,json:async()=>url.startsWith('https:')?
   {open:true,quotes:{vix:{v:30,open:true},spx:{v:100,open:false}}}:
   JSON.parse(fs.readFileSync(path.join(root,'timing',url.split('?')[0]),'utf8'))};
 };
 await run('load()');await run('loadLong()');await run('loadBT()');await run('loadLive()');
 assert.deepEqual(urls.slice(0,3).map(u=>u.split('?')[0]),['../data/dashboard/market.json','../data/dashboard/market-long.json','../data/dashboard/backtest.json']);
 assert.equal(new URL(urls[3]).searchParams.get('quotes'),'spx,ndx,fng');
 assert.equal(run('LIVE.quotes.vix'),undefined);assert.equal(run('LIVE.open'),false);
 assert.equal(run('BT.indices.spx.curve.vix'),undefined);
});
test('date-only labels stay on the exchange date in New York',()=>{
 const before=process.env.TZ;process.env.TZ='America/New_York';
 try{const {run}=page();run('LANG="en";LOCALE="en-US"');assert.equal(run('fdate("2026-09-23")'),'Sep 23, 2026')}
 finally{if(before===undefined)delete process.env.TZ;else process.env.TZ=before}
});
test('hover uses actual irregular date positions, including both edges',()=>{
 const {run}=page();
 assert.equal(run('nearestIndex([10,20,250,251],20)'),1);
 assert.equal(run('nearestIndex([10,20,250,251],248)'),2);
 assert.equal(run('nearestIndex([10,20,250,251],-100)'),0);
 assert.equal(run('nearestIndex([10,20,250,251],999)'),3);
});
test('weekly holiday spacing stays connected but a multi-month gap breaks',()=>{
 const {run}=page();
 assert.equal(run('pointRuns([["2020-09-11",50],["2020-09-18",52],["2021-02-05",68],["2021-02-12",70]]).length'),2);
 assert.equal(run('pointRuns([["2026-01-02",1],["2026-01-12",2]]).length'),1);
});
test('real chart hover never invents a gauge observation on a missing date',()=>{
 const {run,node}=page();
 run('LONG='+fs.readFileSync(path.join(root,'data/market-long.json'),'utf8')+';');
 run('attachHover=(box,m)=>{window.hover=m};state.range.main=365*5;PAN=1095;renderMain();');
 const shown=run('Array.from({length:window.hover.n},(_,k)=>window.hover.html(k)).find(s=>s.includes("2020.12.18"))');
 assert.match(shown,/관측값 없음/);assert.doesNotMatch(shown,/<b>52<\/b>/);
 assert.match(node('main-chart').innerHTML,/<svg/);
 run('for(let k=0;k<window.hover.n;k++){if(window.hover.nearest(window.hover.X(k))!==k)throw Error("wrong date "+k)}');
});
test('statistics show each index count and period without undefined',()=>{
 const {run,node}=page(true);
 run('BT='+fs.readFileSync(path.join(root,'data/backtest.json'),'utf8')+';btAx="vix";btH="1Y";DATA={vix:{value:15,date:"2026-09-23"}};btSummary();');
 const text=node('bt-sum').innerHTML;
 assert.match(text,/1993–/);assert.match(text,/1999–/);assert.doesNotMatch(text,/undefined/);
 for(const key of ['spx','ndx']){
  const count=run('num(BT.indices["'+key+'"].curve.vix.h["1Y"].n[15])');
  assert.ok(text.includes(count));
 }
 run('BTGEO=btGeo();attachHover=(box,m)=>{window.hover=m};btHover();');
 assert.doesNotMatch(run('window.hover.html(17)'),/undefined/);
});
test('closed market polls in ten minutes and then returns to minute polling',async()=>{
 const {run,timers,ctx}=page();let calls=0;
 run('LIVE={open:false};');
 ctx.loadLive=async()=>{calls++;run('LIVE={open:true}');};
 run('liveLoop()');let pending=[...timers.values()].at(-1);
 assert.equal(pending.ms,600000);await pending.fn();assert.equal(calls,1);
 assert.equal([...timers.values()].at(-1).ms,60000);
 ctx.document.hidden=true;await [...timers.values()].at(-1).fn();assert.equal(calls,1);
});
test('returning to tab requests immediately without overlapping requests',async()=>{
 const {run,timers,ctx,listeners}=page();let calls=0,finish;
 ctx.loadLive=()=>{calls++;return new Promise(r=>{finish=r})};
 run('LIVE={open:false};liveLoop()');listeners.visibilitychange();listeners.visibilitychange();
 assert.equal(calls,1);finish();await new Promise(r=>setImmediate(r));
 assert.equal([...timers.values()].at(-1).ms,600000);
});
test('a stuck quote request times out and schedules another check',async()=>{
 const {run,timers,ctx}=page();
 ctx.console={...console,error:()=>{}};
 ctx.fetch=(url,{signal})=>new Promise((resolve,reject)=>{
  signal.addEventListener('abort',()=>reject(new Error('aborted')));
 });
 run('LIVE={open:true};liveLoop()');
 const ticking=[...timers.values()].at(-1).fn();
 const timeout=[...timers.values()].find(t=>t.ms===10000);
 assert.ok(timeout);timeout.fn();await ticking;
 assert.equal([...timers.values()].at(-1).ms,60000);
});
test('live arriving before history is applied when history arrives',async()=>{
 const {run,ctx}=page();
 run('renderMain=()=>{};renderBT=()=>{};calibrateDraw=()=>{};');
 ctx.fetch=async url=>({ok:true,json:async()=>url.includes('test.invalid')?
  {quotes:{spx:{v:200,d:'2026-09-23'}},open:false,fetched:'2026-09-24T00:00:00Z'}:
  {series:{spx:{series:[['2026-09-21',100],['2026-09-22',101]],ticker:'SPY'}}}});
 await run('loadLive()');await run('loadLong()');
 assert.equal(run('LONG.series.spx.series.at(-1)[1]'),200);
 assert.equal(run('LONG.series.spx.series.at(-1)[0]'),'2026-09-23');
});
test('newer daily quote beats older live gauge and survives daily-file failure',()=>{
 const {run}=page();
 run('btAx="vix";DATA={vix:{value:15,date:"2026-09-23"}};LIVE={quotes:{vix:{v:20,d:"2026-09-22"}}}');
 assert.equal(run('axNow()'),15);
 run('DATA=null;LONG={series:{vix:{series:[["2026-09-23",16]]}}}');
 assert.equal(run('axNow()'),16);
});
test('language repaint and daily response cannot erase quote-check time',async()=>{
 const {run,ctx,node}=page();
 run('LIVE={quotes:{spx:{v:200,d:"2026-09-23"}},fetched:"2026-09-24T00:00:00Z"};STAMP_ISO="2026-09-20T00:00:00Z";paintStamp();');
 assert.match(node('stamp').textContent,/시세 조회/);
 run('LANG="en";L10N=D.en;LOCALE="en-US";paintStatic();');
 assert.match(node('stamp').textContent,/Quotes checked/);
 ctx.fetch=async()=>({ok:true,json:async()=>({updated:'2026-09-20T00:00:00Z'})});
 await run('load()');assert.match(node('stamp').textContent,/Quotes checked/);
});
