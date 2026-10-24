// The six visitor-stats loaders and the /notrack/ page: an opted-out browser must not load Umami at all.
// No network: the inline loader and the opt-out script run in a tiny fake DOM.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {test}=require('node:test'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const pages=['index.html','timing/index.html','titans/index.html','titans/13f/index.html','samuel/index.html','olympics/index.html'];
const ID='41e07a57-a87c-403b-bdf8-e12d911457b6';

function storage(init={},broken=false){
  const m=new Map(Object.entries(init));
  const guard=()=>{if(broken)throw new Error('SecurityError');};
  return {map:m,getItem:k=>(guard(),m.has(k)?m.get(k):null),setItem:(k,v)=>(guard(),m.set(k,String(v))),removeItem:k=>(guard(),m.delete(k))};
}
function loader(file){
  const blocks=[...read(file).matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(s=>s.includes('cloud.umami.is'));
  assert.equal(blocks.length,1,file);
  return blocks[0];
}
function runLoader(file,{host='itpaidoff.com',store=storage()}={}){
  const added=[],el=()=>({attrs:{},setAttribute(k,v){this.attrs[k]=v;}});
  const ctx=vm.createContext({location:{hostname:host},localStorage:store,
    document:{createElement:el,head:{appendChild:n=>{added.push(n);return n;}}}});
  ctx.window=ctx;
  vm.runInContext(loader(file),ctx);
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
