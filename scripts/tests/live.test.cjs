const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {test}=require('node:test'),assert=require('node:assert/strict');
const code=fs.readFileSync(path.resolve(__dirname,'../../workers/live.js'),'utf8').replace('export default {','globalThis.worker = {');
function worker(fail=''){
 const requests=[];
 const ctx={URL,Response,Date,fetch:async url=>{
  requests.push(url);
  if(fail&&url.includes(fail))throw Error('source unavailable');
  return {ok:true,json:async()=>url.includes('cnn.io')?{fear_and_greed:{score:37,timestamp:'2026-09-25T23:59:59Z'}}:
   {chart:{result:[{meta:{regularMarketPrice:100,regularMarketTime:1790352000}}]}}};
 }};
 vm.createContext(ctx);vm.runInContext(code,ctx);
 return {fetch:query=>ctx.worker.fetch(new Request('https://example.test/'+query)),requests};
}
test('filtered live request neither fetches nor sends VIX',async()=>{
 const w=worker(),r=await w.fetch('?quotes=spx,ndx,fng'),j=await r.json();
 assert.equal(r.status,200);assert.deepEqual(Object.keys(j.quotes).sort(),['fng','ndx','spx']);
 assert.equal(w.requests.length,3);assert.ok(w.requests.every(url=>!url.includes('VIX')));
});
test('default live response retains all four series for restoring VIX',async()=>{
 const w=worker(),j=await (await w.fetch('')).json();
 assert.deepEqual(Object.keys(j.quotes).sort(),['fng','ndx','spx','vix']);assert.equal(w.requests.length,4);
});
test('unknown or empty selections are rejected before upstream requests',async()=>{
 for(const q of ['?quotes=','?quotes=__proto__','?quotes=spx,unknown']){
  const w=worker();assert.equal((await w.fetch(q)).status,400);assert.equal(w.requests.length,0);
 }
});
test('one selected source failing preserves the other quotes',async()=>{
 const w=worker('QQQ'),j=await (await w.fetch('?quotes=spx,ndx,fng')).json();
 assert.deepEqual(Object.keys(j.quotes).sort(),['fng','spx']);
 assert.deepEqual(j.failed,['ndx: source unavailable']);assert.equal(j.open,false);
});
