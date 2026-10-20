const {test}=require('node:test'),assert=require('node:assert/strict');
const P=require('../../olympics/presentation.js'),M=require('../../olympics/model.js');
const fs=require('node:fs'),path=require('node:path');
test('drawdown moment retains the actual earlier peak rather than the eventual high',()=>{
  const r={options:{amount:100},curve:[100,120,90,110,140,130].map((v,i)=>({day:String(i),values:{emma:v}}))};
  assert.deepEqual(P.drawdownMoment(r,'emma'),{index:2,peakIndex:1,drop:-.25,peak:120,value:90});
  r.curve=r.curve.slice(0,2);assert.equal(P.drawdownMoment(r,'emma'),null);
});
test('a tiny decline is retained and equal worst drops select the first actual occurrence',()=>{
  const r={options:{amount:100},curve:[100,99.99,100,99.99].map(v=>({values:{john:v}}))};
  assert.equal(P.drawdownMoment(r,'john').index,1);assert.ok(P.drawdownMoment(r,'john').drop<0);
});
test('first purchase ignores sales and other people, and absent purchases produce no moment',()=>{
  const trades=[{actor:'daniel',action:'sell',day:'01'},{actor:'emma',action:'buy',day:'01'},{actor:'daniel',action:'buy',day:'02'}];
  const r={trades,curve:[{day:'01'},{day:'02'}]};
  assert.deepEqual(P.firstTrade(r,'daniel'),{index:1,trade:trades[2]});assert.equal(P.firstTrade(r,'alicia'),null);
});
test('trade groups preserve execution order and cents, separate disclosures, and exclude future choices',()=>{
  const t=(day,actor,action,amount,filed='F',period='Q')=>({day,actor,action,amount,filed,period});
  const trades=[t('01','alicia','sell',1.23),t('01','alicia','buy',2.34),t('01','alicia','buy',3.45),
    t('01','alicia','buy',8,'OTHER'),t('01','samuel','buy',10),t('02','alicia','sell',20)];
  const before=JSON.stringify(trades),groups=P.groupTrades(trades,'01','alicia');
  assert.equal(groups.length,2);assert.equal(groups[0].sell,1.23);assert.ok(Math.abs(groups[0].buy-5.79)<1e-10);
  assert.deepEqual(groups[0].trades,trades.slice(0,3));assert.equal(groups[1].buy,8);assert.equal(JSON.stringify(trades),before);
  assert.equal(P.groupTrades(trades,'02')[0].day,'02');assert.equal(P.groupTrades(trades,'00').length,0);
});
test('real-data moments and trade groups reconcile with the unmodified engine in both benchmarks',()=>{
  const raw=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data/olympics/race.json'),'utf8'));
  for(const asset of ['spx','ndx']){
    const r=M.run(raw,{asset,amount:10000}),before=JSON.stringify(r),final=r.curve.at(-1);
    for(const id of M.ids){
      const low=P.drawdownMoment(r,id),rank=M.rank(final,10000).find(x=>x.id===id);
      assert.ok(Math.abs((low?.drop||0)-rank.drop)<1e-10);
      const first=P.firstTrade(r,id);if(first)assert.equal(r.curve[first.index].day,first.trade.day);
      const day=r.curve[Math.floor(r.curve.length/2)].day,groups=P.groupTrades(r.trades,day,id);
      const all=groups.flatMap(g=>g.trades),expected=r.trades.filter(t=>t.day<=day&&t.actor===id);
      assert.equal(all.length,expected.length);
      for(const action of ['buy','sell'])assert.ok(Math.abs(groups.reduce((s,g)=>s+g[action],0)-expected.filter(t=>t.action===action).reduce((s,t)=>s+t.amount,0))<1e-6);
    }assert.equal(JSON.stringify(r),before);
  }
});
