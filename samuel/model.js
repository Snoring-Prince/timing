/* Pure historical calculations; shared by the page and regression tests. */
(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.SamuelModel=factory();
})(typeof window==='undefined'?this:window,function(){
  'use strict';
  const DAY=86400000;
  function validDate(day){return typeof day==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(day)&&Number.isFinite(Date.parse(day))&&new Date(day).toISOString().slice(0,10)===day;}
  function series(data,key){
    const item=data?.series?.[key];
    if(data?.version!==1||data.basis!=='dividend-adjusted'||data.frequency!=='daily'||item?.ticker!==({spx:'SPY',ndx:'QQQ'})[key])throw Error('data');
    if(!Array.isArray(item.series)||item.series.length<2)throw Error('data');
    const rows=item.series;
    for(let i=0;i<rows.length;i++){
      const r=rows[i];
      if(!Array.isArray(r)||!validDate(r[0])||typeof r[1]!=='number'||!Number.isFinite(r[1])||r[1]<=0||
        (i&&(r[0]<=rows[i-1][0]||Date.parse(r[0])-Date.parse(rows[i-1][0])>10*DAY)))throw Error('data');
    }
    return rows;
  }
  function lowerBound(rows,day){let lo=0,hi=rows.length;while(lo<hi){const m=(lo+hi)>>1;if(rows[m][0]<day)lo=m+1;else hi=m;}return lo;}
  function addMonths(day,n){
    const d=new Date(day),y=d.getUTCFullYear(),m=d.getUTCMonth()+n;
    const last=new Date(Date.UTC(y,m+1,0)).getUTCDate();
    return new Date(Date.UTC(y,m,Math.min(d.getUTCDate(),last))).toISOString().slice(0,10);
  }
  function monthStart(day,n){const d=new Date(day);return new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+n,1)).toISOString().slice(0,10);}
  function simulate(rows,month,{amount=10000,months=6,years=3,rate=0}={}){
    if(!/^\d{4}-\d{2}$/.test(month)||!validDate(month+'-01')||!Number.isFinite(amount)||amount<=0||amount>1e9||
      ![3,6,12].includes(months)||![1,3,5,10].includes(years)||!Number.isFinite(rate)||rate<0||rate>20)throw Error('inputs');
    const start=lowerBound(rows,month+'-01');
    if(start>=rows.length||rows[start][0].slice(0,7)!==month)throw Error('range');
    const from=rows[start][0],target=addMonths(from,years*12),end=lowerBound(rows,target);
    if(end>=rows.length||Date.parse(rows[end][0])-Date.parse(target)>7*DAY)throw Error('range');
    const schedule=[];
    for(let i=0;i<months;i++){
      const due=i===0?from:monthStart(from,i),at=lowerBound(rows,due);
      if(at>end||Date.parse(rows[at][0])-Date.parse(due)>7*DAY)throw Error('range');
      schedule.push(at);
    }
    const lumpUnits=amount/rows[start][1],part=amount/months;
    let units=0,cash=amount,next=0,previous=Date.parse(from),peakL=amount,peakS=amount,mddL=0,mddS=0;
    const curve=[],buys=[];
    for(let i=start;i<=end;i++){
      const [day,price]=rows[i],time=Date.parse(day);
      cash*=Math.pow(1+rate/100,(time-previous)/(DAY*365.25));previous=time;
      if(next<schedule.length&&i===schedule[next]){
        // The entire principal is available from day one. Interest stays in cash.
        const deposit=next===months-1?amount-part*(months-1):part;
        units+=deposit/price;cash-=deposit;if(Math.abs(cash)<1e-7)cash=0;
        buys.push({day,amount:deposit});next++;
      }
      const lump=lumpUnits*price,split=units*price+cash;
      peakL=Math.max(peakL,lump);peakS=Math.max(peakS,split);
      mddL=Math.min(mddL,lump/peakL-1);mddS=Math.min(mddS,split/peakS-1);
      curve.push({day,lump,split,cash});
    }
    const last=curve.at(-1);
    return {from,to:last.day,amount,months,years,rate,curve,buys,lump:last.lump,split:last.split,cash:last.cash,
      returnL:last.lump/amount-1,returnS:last.split/amount-1,mddL,mddS};
  }
  function cohorts(rows,options){
    const starts=new Set(rows.map(r=>r[0].slice(0,7))),results=[];
    for(const month of starts){try{const r=simulate(rows,month,{...options,amount:10000});results.push({month,lump:r.returnL,split:r.returnS,mddL:r.mddL,mddS:r.mddS});}catch(e){if(e.message!=='range')throw e;}}
    return results;
  }
  function summarize(results){
    if(!results.length)return null;
    const median=values=>{const sorted=values.slice().sort((a,b)=>a-b),n=sorted.length;return n%2?sorted[(n-1)/2]:(sorted[n/2-1]+sorted[n/2])/2;};
    const eps=1e-9,lump=results.filter(r=>r.lump-r.split>eps).length,split=results.filter(r=>r.split-r.lump>eps).length;
    return {n:results.length,lump,split,ties:results.length-lump-split,medianL:median(results.map(r=>r.lump)),medianS:median(results.map(r=>r.split))};
  }
  return {series,simulate,cohorts,summarize,lowerBound,addMonths};
});
