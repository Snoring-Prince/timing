// Execute the loader referenced by each public page without contacting Umami.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {test}=require('node:test'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const pages=['index.html','timing/index.html','titans/index.html','titans/13f/index.html','samuel/index.html','olympics/index.html'];
for(const investor of JSON.parse(read('data/titans/investors.json')).investors){
  if(investor.active!==false)pages.push(`titans/${investor.slug}/index.html`);
}
const ID='41e07a57-a87c-403b-bdf8-e12d911457b6';

function storage(init={},broken=false){
  const m=new Map(Object.entries(init));
  const guard=()=>{if(broken)throw new Error('SecurityError');};
  return {map:m,getItem:k=>(guard(),m.has(k)?m.get(k):null),setItem:(k,v)=>(guard(),m.set(k,String(v))),removeItem:k=>(guard(),m.delete(k))};
}
function loader(file){
  const html=read(file);
  const blocks=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(s=>s.includes('cloud.umami.is'));
  for(const match of html.matchAll(/<script\b[^>]*\bsrc="\/(shared\/stats\.js)(?:\?[^"]*)?"[^>]*>/g))blocks.push(read(match[1]));
  assert.equal(blocks.length,1,file);
  return blocks[0];
}
function runLoader(file,{host='itpaidoff.com',store=storage(),ctxOut}={}){
  const added=[],el=()=>({attrs:{},on:{},setAttribute(k,v){this.attrs[k]=v;},addEventListener(t,f){(this.on[t]||=[]).push(f);}});
  const ctx=vm.createContext({location:{hostname:host},localStorage:store,
    document:{createElement:el,head:{appendChild:n=>{added.push(n);return n;}}}});
  ctx.window=ctx;
  vm.runInContext(loader(file),ctx);
  if(ctxOut)ctxOut.ctx=ctx;
  return added.filter(n=>/cloud\.umami\.is/.test(n.src||''));
}

for(const file of pages)test(`${file}: loads Umami for visitors, but not on an opted-out or local browser`,()=>{
  const counted=runLoader(file);
  assert.equal(counted.length,1);
  assert.equal(counted[0].attrs['data-website-id'],ID);
  assert.equal(runLoader(file,{store:storage({'umami.disabled':'1'})}).length,0,'opted-out browser still loads Umami');
  assert.equal(runLoader(file,{store:storage({},true)}).length,1,'blocked storage must not stop ordinary counting');
  assert.equal(runLoader(file,{host:'localhost'}).length,0);
});

function notrack(store){
  const html=read('notrack/index.html'),script=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).at(-1);
  const nodes=[...html.matchAll(/<\w+[^>]*\bdata-show="(\w+)"[^>]*>/g)].map(m=>({id:(m[0].match(/\bid="([^"]+)"/)||[])[1],show:m[1],
    hidden:/\bhidden\b/.test(m[0]),getAttribute(){return this.show;}}));
  const byId={state:{attrs:{},setAttribute(k,v){this.attrs[k]=v;}}},handlers={};
  for(const n of nodes)if(n.id)byId[n.id]=Object.assign(n,{addEventListener:(t,f)=>{handlers[n.id]=f;}});
  const ctx=vm.createContext({localStorage:store,document:{getElementById:id=>byId[id],querySelectorAll:()=>nodes}});
  vm.runInContext(script,ctx);
  const shown=()=>nodes.filter(n=>!n.hidden).map(n=>n.id||n.show).sort().join(',');
  return {byId,handlers,shown};
}

test('notrack/index.html: opening it opts the browser out, the button undoes it, and the screen tells the truth',()=>{
  const html=read('notrack/index.html');
  assert.match(html,/<meta name="robots" content="noindex">/);
  assert.doesNotMatch(html,/cloud\.umami\.is/,'the opt-out page itself must not load Umami');
  assert.doesNotMatch(read('sitemap.xml'),/notrack/);
  assert.ok([...html.matchAll(/<\w+[^>]*\bdata-show="\w+"[^>]*>/g)].every(m=>/\bhidden\b/.test(m[0])),'without JavaScript no state may be claimed');
  const store=storage(),p=notrack(store);
  assert.equal(store.map.get('umami.disabled'),'1');
  assert.equal(p.byId.state.attrs['data-state'],'off');
  assert.equal(p.shown(),'count-again,off');
  p.handlers['count-again']();
  assert.equal(store.map.has('umami.disabled'),false);
  assert.equal(p.shown(),'on,stop-counting');
  p.handlers['stop-counting']();
  assert.equal(store.map.get('umami.disabled'),'1');
  const blocked=notrack(storage({},true));
  assert.equal(blocked.byId.state.attrs['data-state'],'na');
  assert.equal(blocked.shown(),'na');
});

// 2026-11-23 review: clicks made while Umami was still loading were dropped. On the
// Olympics page the first character / result / comparison clicks often came first.
test('shared/stats.js keeps clicks made before Umami loads and sends them once, in order',()=>{
  const out={},[script]=runLoader('olympics/index.html',{ctxOut:out}),{ctx}=out,sent=[];
  ctx.track('olympics_character',{person:'alicia'});ctx.track('olympics_result',{person:'alicia'});
  assert.deepEqual(sent,[]);
  ctx.umami={track:(n,d)=>sent.push([n,d&&d.person])};
  for(const f of script.on.load)f();
  ctx.track('olympics_compare');
  assert.deepEqual(sent,[['olympics_character','alicia'],['olympics_result','alicia'],['olympics_compare',undefined]]);
  for(const f of script.on.load)f();
  assert.equal(sent.length,3,'a second load event must not resend');
  // Blocked by an ad blocker: nothing is held for ever and nothing throws.
  const out2={},[blocked]=runLoader('samuel/index.html',{ctxOut:out2});
  out2.ctx.track('samuel_compare');for(const f of blocked.on.error)f();
  for(let i=0;i<50;i++)out2.ctx.track('samuel_compare');
  out2.ctx.umami={track:()=>{throw new Error('down');}};
  for(const f of blocked.on.load||[])f();
  assert.doesNotThrow(()=>out2.ctx.track('samuel_compare'));
});
