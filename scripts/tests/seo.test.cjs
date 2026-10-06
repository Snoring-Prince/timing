// Execute the actual metadata painters in a minimal DOM; no network or packages.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {test}=require('node:test'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const investors=JSON.parse(read('data/titans/investors.json')).investors;
const pages=['index.html','timing/index.html','samuel/index.html','titans/index.html','titans/13f/index.html',
  ...investors.map(i=>`titans/${i.slug}/index.html`)];

function painter(file,search){
  const html=read(file),nodes=[];
  const node=()=>({attrs:{},setAttribute(k,v){this.attrs[k]=v;return this;}});
  for(const selector of ['meta[name="description"]','meta[property="og:title"]','meta[property="og:description"]',
    'meta[property="og:locale"]','meta[property="og:locale:alternate"]','meta[property="og:image"]','meta[property="og:url"]']){
    const n=node();n.selector=selector;nodes.push(n);
  }
  const head={querySelector:s=>nodes.find(n=>s==='link[rel="canonical"]'?n.attrs.rel==='canonical':n.selector===s)||null,
    appendChild:n=>{nodes.push(n);return n;}};
  const ctx=vm.createContext({URLSearchParams,Intl,Date,URL,console,window:{},navigator:{languages:['en-US']},
    location:{search},localStorage:{getItem:()=>null},document:{head,createElement:node,documentElement:{getAttribute:()=>null}}});
  let source,call;
  if(file==='timing/index.html'){
    source=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(s=>s.includes('const D='));
    source=source.replace('applyLang(pickLang(),false);','');call='document.title=tx("docTitle");paintHead();';
  }else if(file.startsWith('titans/')&&!['titans/index.html','titans/13f/index.html'].includes(file)){
    const config=html.match(/<script>\s*(window\.TITAN[\s\S]*?)<\/script>/)[1];
    const shared=read('titans/shared/investor.js');
    source=config+'\n'+shared.slice(0,shared.indexOf('/* 곁들이 표 둘'));
    call='document.title=tx("docTitle",tName(),TT.since);paintHead();';
  }else{
    const app=file==='samuel/index.html'?read('samuel/app.js'):html;
    const headCode=app.match(/const HEAD=({[\s\S]*?\n  });/)[0];
    const fnName=['titans/index.html','samuel/index.html'].includes(file)?'paintHead':'paint';
    let body=app.slice(app.indexOf(`  function ${fnName}(){`));
    body=body.slice(0,body.indexOf('\n  }')+4);
    if(fnName==='paint')body=body.slice(0,body.indexOf('    document.querySelectorAll('))+'\n  }';
    source='let LANG="en";\n'+headCode+'\n'+body;call=fnName+'();';
  }
  vm.runInContext(source,ctx);
  return {ctx,nodes,head,paint(lang){vm.runInContext(`LANG=${JSON.stringify(lang)};if(typeof D!=="undefined")L10N=D[LANG];${call}`,ctx)}};
}

for(const file of pages)test(`${file}: English, Korean and default metadata survive repeated language painting`,()=>{
  const base='https://itpaidoff.com/'+file.replace(/index\.html$/,'');
  for(const query of ['', '?lang=en&from=test#fragment', '?lang=ko&from=test']){
    const p=painter(file,query);
    for(const lang of ['ko','en','ko']){
      p.paint(lang);
      const canonical=p.head.querySelector('link[rel="canonical"]');
      assert.equal(p.nodes.filter(n=>n.attrs.rel==='canonical').length,1);
      const want=base+(query?'?lang='+lang:'');
      assert.equal(canonical.attrs.href,want);
      assert.equal(p.head.querySelector('meta[property="og:url"]').attrs.content,want);
      assert.equal(p.head.querySelector('meta[property="og:locale"]').attrs.content,lang==='ko'?'ko_KR':'en_US');
      const description=p.head.querySelector('meta[name="description"]').attrs.content;
      assert.ok(description?.length>20);
      assert.equal(/[가-힣]/.test(description),lang==='ko');
      const title=p.head.querySelector('meta[property="og:title"]').attrs.content;
      assert.equal(/[가-힣]/.test(title),lang==='ko');
      assert.equal(p.ctx.document.title,title);
    }
  }
});
