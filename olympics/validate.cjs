// Offline publication gate. Uses exactly the browser's pure engine and strategy modules.
const fs=require('node:fs'),M=require('./model.js');
const p=M.prepare(JSON.parse(fs.readFileSync(0,'utf8')));
const starts=[...new Set(p.days.map(d=>d.slice(0,7)))].map(month=>p.days.find(d=>d.startsWith(month))).filter(d=>d<p.days.at(-1));
for(const asset of ['spx','ndx'])for(const start of starts)for(const percent of [20,100]){
  const result=M.run(p,{asset,start,buy:percent,sell:percent,alicia:percent,monthly:percent===20?1:10});
  if(result.curve.length<2||Object.keys(result.curve.at(-1).values).length!==5)throw Error('incomplete race');
}
console.log(`Race validated: ${starts.length} starts × 2 ETFs × 2 allocation settings`);
