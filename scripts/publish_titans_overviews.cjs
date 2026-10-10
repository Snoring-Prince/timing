#!/usr/bin/env node
// No network: publish the exact same bilingual summary shown by the browser.
const fs=require('node:fs');
const path=require('node:path');
const overview=require('../titans/shared/overview.js');
const START='<!-- TITAN-OVERVIEW:START -->', END='<!-- TITAN-OVERVIEW:END -->';

function replaceOverview(html,section){
  const block=`${START}\n${section}\n${END}`;
  const starts=html.split(START).length-1, ends=html.split(END).length-1;
  if(starts===0&&ends===0){
    // A new investor shell may predate the generator. Never guess another page.
    if(!/id="static-investor"/.test(html)||html.split('</main>').length!==2)
      throw new Error('Missing investor shell');
    return html.replace('</main>',`${block}\n</main>`);
  }
  if(starts!==1||ends!==1||html.indexOf(START)>html.indexOf(END))throw new Error('Invalid overview markers');
  return html.slice(0,html.indexOf(START))+block+html.slice(html.indexOf(END)+END.length);
}

function publish(root=path.resolve(__dirname,'..'),{check=false}={}){
  const registry=JSON.parse(fs.readFileSync(path.join(root,'data/titans/investors.json'),'utf8'));
  const changes=[], errors=[];
  for(const inv of registry.investors.filter(i=>i.active!==false)){
    try{
      if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(inv.slug)||!inv.name.en||!inv.name.ko)
        throw new Error('Invalid investor registry entry');
      const book=JSON.parse(fs.readFileSync(path.join(root,`data/titans/${inv.slug}.json`),'utf8'));
      if(String(book.manager?.cik||'').padStart(10,'0')!==inv.cik)throw new Error('Investor CIK mismatch');
      const file=path.join(root,`titans/${inv.slug}/index.html`), html=fs.readFileSync(file,'utf8');
      if(!html.includes('../shared/overview.js?'))throw new Error('Missing shared overview script');
      const next=replaceOverview(html,overview.section(book,inv));
      if(next!==html)changes.push({file,next,slug:inv.slug});
    }catch(err){errors.push(`${inv.slug}: ${err.message}`);}
  }
  // Validate all inputs before touching any page. An error preserves every old snapshot.
  if(errors.length)throw new Error(errors.join('\n'));
  if(check&&changes.length)throw new Error(`Stale investor overviews: ${changes.map(c=>c.slug).join(', ')}`);
  if(!check)for(const {file,next} of changes){
    fs.writeFileSync(file+'.tmp',next,'utf8');fs.renameSync(file+'.tmp',file);
  }
  return changes.map(c=>c.slug);
}
if(require.main===module){
  try{
    const changes=publish(undefined,{check:process.argv.includes('--check')});
    console.log(changes.length?`Updated overviews: ${changes.join(', ')}`:'Investor overviews unchanged');
  }catch(err){console.error(err.message);process.exitCode=1;}
}
module.exports={publish,replaceOverview};
