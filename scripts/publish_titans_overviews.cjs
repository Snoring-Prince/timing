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

// A registered investor whose filings are not fetched yet has no summary. A shell
// copied from another investor must not keep that investor's snapshot.
function removeOverview(html){
  const starts=html.split(START).length-1, ends=html.split(END).length-1;
  if(starts===0&&ends===0)return html;
  if(starts!==1||ends!==1||html.indexOf(START)>html.indexOf(END))throw new Error('Invalid overview markers');
  const after=html.indexOf(END)+END.length;
  return html.slice(0,html.indexOf(START))+html.slice(html[after]==='\n'?after+1:after);
}

// The page's own price file (window.TITAN.prices), read the way the browser does:
// missing or unreadable means no tickers, never a failure.
function tickersFor(root,slug,html){
  const m=html.match(/\bprices:\s*"\.\.\/\.\.\/data\/titans\/prices\/([a-z0-9-]+)\.json"/);
  if(!m||m[1]!==slug)return {};
  try{return overview.tickersFrom(JSON.parse(fs.readFileSync(path.join(root,`data/titans/prices/${slug}.json`),'utf8')));}
  catch{return {};}
}

function publish(root=path.resolve(__dirname,'..'),{check=false}={}){
  const registry=JSON.parse(fs.readFileSync(path.join(root,'data/titans/investors.json'),'utf8'));
  const changes=[], errors=[];
  for(const inv of registry.investors.filter(i=>i.active!==false)){
    try{
      if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(inv.slug)||!inv.name.en||!inv.name.ko)
        throw new Error('Invalid investor registry entry');
      const file=path.join(root,`titans/${inv.slug}/index.html`), html=fs.readFileSync(file,'utf8');
      if(!html.includes('../shared/overview.js?'))throw new Error('Missing shared overview script');
      const bookFile=path.join(root,`data/titans/${inv.slug}.json`);
      let next;
      if(!fs.existsSync(bookFile)){
        // Same rule as the price job: only no book AND no price file means "registered,
        // not fetched yet". A lost book with prices left behind is a failure, not a reset.
        if(fs.existsSync(path.join(root,`data/titans/prices/${inv.slug}.json`)))
          throw new Error('Filing book missing while its price file exists');
        next=removeOverview(html);
      }else{
        const book=JSON.parse(fs.readFileSync(bookFile,'utf8'));
        if(String(book.manager?.cik||'').padStart(10,'0')!==inv.cik)throw new Error('Investor CIK mismatch');
        next=replaceOverview(html,overview.section(book,inv,tickersFor(root,inv.slug,html)));
      }
      if(next!==html)changes.push({file,next,slug:inv.slug});
    }catch(err){errors.push(`${inv.slug}: ${err.message}`);}
  }
  // Each investor stands alone: a bad book keeps that page's old snapshot and
  // fails the run (alert), while the other investors' pages still update.
  if(check){
    const stale=changes.length?[`Stale investor overviews: ${changes.map(c=>c.slug).join(', ')}`]:[];
    if(stale.length||errors.length)throw new Error([...errors,...stale].join('\n'));
  }else for(const {file,next} of changes){
    fs.writeFileSync(file+'.tmp',next,'utf8');fs.renameSync(file+'.tmp',file);
  }
  if(errors.length){
    const done=changes.length?`\nUpdated overviews: ${changes.map(c=>c.slug).join(', ')}`:'';
    throw new Error(errors.join('\n')+done);
  }
  return changes.map(c=>c.slug);
}
if(require.main===module){
  try{
    const changes=publish(undefined,{check:process.argv.includes('--check')});
    console.log(changes.length?`Updated overviews: ${changes.join(', ')}`:'Investor overviews unchanged');
  }catch(err){console.error(err.message);process.exitCode=1;}
}
module.exports={publish,replaceOverview,removeOverview};
