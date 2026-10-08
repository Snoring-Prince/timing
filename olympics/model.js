(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory(['john','daniel','samuel','alicia','emma'].map(k=>require('./strategies/'+k+'.js')));
  else root.OlympicModel=factory(['john','daniel','samuel','alicia','emma'].map(k=>root.OlympicStrategies[k]));
})(typeof window==='undefined'?this:window,function(strategies){
  'use strict';
  const DAY=86400000,defaults={amount:10000,asset:'spx',fear:10,greed:90,buy:20,sell:20,monthly:5,alicia:20,repeat:false};
  const date=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
  function rows(a,max=Infinity){
    if(!Array.isArray(a)||!a.length)throw Error('data');
    for(let i=0;i<a.length;i++)if(!Array.isArray(a[i])||!date(a[i][0])||typeof a[i][1]!=='number'||!Number.isFinite(a[i][1])||a[i][1]<=0||a[i][1]>max||(i&&a[i][0]<=a[i-1][0]))throw Error('data');
    return new Map(a);
  }
  function prepare(data){
    if(data?.version!==1||data.basis!=='dividend-adjusted'||!date(data.from)||!date(data.to)||data.from>=data.to)throw Error('data');
    const maps={spx:rows(data.etfs.spx),ndx:rows(data.etfs.ndx),reserve:rows(data.etfs.reserve)};
    const days=data.etfs.spx.map(r=>r[0]).filter(d=>d>=data.from&&d<=data.to);
    if(days.length<2||days[0]!==data.from||days.at(-1)!==data.to)throw Error('data');
    for(let i=0;i<days.length;i++)if(!maps.ndx.has(days[i])||!maps.reserve.has(days[i])||(i&&Date.parse(days[i])-Date.parse(days[i-1])>10*DAY))throw Error('data');
    const fear=new Map();let prior='';
    for(const [d,v] of data.fear||[]){if(!date(d)||d<=prior||typeof v!=='number'||!Number.isFinite(v)||v<0||v>100)throw Error('data');fear.set(d,v);prior=d;}
    if(!fear.size)throw Error('data');
    for(const [key,stock] of Object.entries(data.stocks||{})){if(stock.ticker!==key)throw Error('data');maps[key]=rows(stock.series);}
    const filings=[];let previous=null;
    for(const e of data.disclosures||[]){
      if(!date(e.filed)||!date(e.period)||e.filed<=e.period||(previous&&e.filed<=previous.filed))throw Error('data');
      if(previous&&e.period<previous.period)throw Error('data');
      const current=new Map();
      for(const h of e.holdings){if(h.key!==h.ticker||current.has(h.key)||!Number.isFinite(h.shares)||h.shares<=0||!Number.isFinite(h.value)||h.value<=0)throw Error('data');current.set(h.key,h);}
      if(previous){
        const old=new Map(previous.holdings.map(h=>[h.key,h])),changes=[];
        for(const key of new Set([...old.keys(),...current.keys()])){
          const a=old.get(key),b=current.get(key);let before=a?.shares||0;
          for(const [d,r] of Object.entries(data.stocks?.[key]?.splits||{}))if(d>previous.period&&d<=e.period){if(!Number.isFinite(r)||r<=0)throw Error('data');before*=r;}
          const after=b?.shares||0,ratio=before?Math.min(1,after/before):1;
          const increase=b?Math.max(0,after-before)*b.value/after:0;
          if(increase>0||ratio<1)changes.push({key,ratio,increase,new:!a});
        }
        filings.push({...e,changes});
      }
      previous=e;
    }
    if(!previous||data.disclosures[0].filed>=data.from)throw Error('data');
    return {data,days,maps,fear,filings};
  }
  function run(input,options={}){
    const p=input.maps?input:prepare(input),o={...defaults,...options};
    const start=o.start||p.data.from,end=o.end||p.data.to;
    if(!date(start)||!date(end)||start>end||start<p.data.from||end>p.data.to)throw Error('range');
    if(!Number.isFinite(o.amount)||o.amount<100||o.amount>1e6||!['spx','ndx'].includes(o.asset)||
      ![o.fear,o.greed,o.buy,o.sell,o.monthly,o.alicia].every(Number.isFinite)||o.fear<0||o.greed>100||o.fear>=o.greed||
      [o.buy,o.sell,o.alicia].some(n=>n<1||n>100)||o.monthly<1||o.monthly>10||typeof o.repeat!=='boolean')throw Error('inputs');
    const days=p.days.filter(d=>d>=start&&d<=end);if(days.length<2)throw Error('range');
    const events=new Map();
    for(const e of p.filings){if(e.filed<days[0]||e.filed>=days.at(-1))continue;const due=days.find(d=>d>e.filed);if(due){const list=events.get(due)||[];list.push(e);events.set(due,list);}}
    const accounts=strategies.map(strategy=>({strategy,state:{},positions:{},reserve:o.amount/p.maps.reserve.get(days[0]),peak:o.amount,mdd:0,stockFlow:0,reserveGain:0,buys:0,sells:0}));
    const curve=[],trades=[];let missingFear=0,greedObserved=false;
    for(let i=0;i<days.length;i++){
      const day=days[i],bil=p.maps.reserve.get(day),price=key=>{const v=p.maps[key]?.get(day);if(!Number.isFinite(v)||v<=0)throw Error('price:'+key+':'+day);return v;};
      const values={},reserves={},drops={},facts={};
      if(i&&!p.fear.has(days[i-1]))missingFear++;
      if(i&&p.fear.get(days[i-1])>=o.greed)greedObserved=true;
      for(const a of accounts){
        // Accrue only the BIL units held overnight; transfers are not profits.
        if(i)a.reserveGain+=a.reserve*(bil-p.maps.reserve.get(days[i-1]));
        const record=(action,key,amount,reason,meta)=>{
          a.stockFlow+=action==='buy'?amount:-amount;a[action==='buy'?'buys':'sells']++;
          trades.push({actor:a.strategy.id,day,action,key,amount,reason,...meta});
        };
        const reserve=()=>a.reserve*bil;
        const buy=(key,wanted,reason,meta={})=>{const amount=Math.min(wanted,reserve());if(amount<1e-8)return;const px=price(key);a.positions[key]=(a.positions[key]||0)+amount/px;a.reserve=Math.max(0,a.reserve-amount/bil);record('buy',key,amount,reason,meta);};
        const sell=(key,wanted,reason,meta={})=>{if(!a.positions[key])return;const px=price(key),amount=Math.min(wanted,a.positions[key]*px);if(amount<1e-8)return;a.positions[key]=Math.max(0,a.positions[key]-amount/px);a.reserve+=amount/bil;record('sell',key,amount,reason,meta);};
        const c={day,first:i===0,asset:o.asset,initial:o.amount,options:o,signalDay:i?days[i-1]:null,
          fear:i?p.fear.get(days[i-1]):undefined,filings:events.get(day)||[],reserve,buy,sell,
          has:key=>(a.positions[key]||0)>1e-8,trim:(key,fraction,reason,meta)=>{if(a.positions[key])sell(key,a.positions[key]*price(key)*fraction,reason,meta);}};
        a.strategy.step(c,a.state);
        let total=reserve();for(const [key,units] of Object.entries(a.positions))if(units>1e-10)total+=units*price(key);
        if(!Number.isFinite(total)||total<0)throw Error('data');a.peak=Math.max(a.peak,total);a.mdd=Math.min(a.mdd,total/a.peak-1);
        values[a.strategy.id]=total;reserves[a.strategy.id]=reserve();drops[a.strategy.id]=a.mdd;
        facts[a.strategy.id]={stockGain:total-reserve()-a.stockFlow,reserveGain:a.reserveGain,buys:a.buys,sells:a.sells};
      }
      curve.push({day,values,reserves,drops,facts,greedObserved});
    }
    return {from:days[0],to:days.at(-1),options:o,curve,trades,missingFear};
  }
  function rank(point,amount){
    const sorted=Object.entries(point.values).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));let prior=null,place=0;
    return sorted.map(([id,value],i)=>{if(prior===null||Math.abs(value-prior)>.005)place=i+1;prior=value;return {id,value,rank:place,return:value/amount-1,reserve:point.reserves[id],drop:point.drops[id]};});
  }
  return {defaults,prepare,run,rank,ids:strategies.map(s=>s.id)};
});
