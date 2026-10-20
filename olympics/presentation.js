(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.OlympicPresentation=factory();
})(typeof window==='undefined'?this:window,function(){
  'use strict';
  // Read the existing account history. This module never changes a strategy or a price.
  function firstTrade(result,actor){
    const trade=result.trades.find(t=>t.actor===actor&&t.action==='buy');
    return trade?{index:result.curve.findIndex(p=>p.day===trade.day),trade}:null;
  }
  function drawdownMoment(result,actor){
    let peak=result.options.amount,peakIndex=0,worst=0,found=null;
    result.curve.forEach((p,index)=>{
      const value=p.values[actor];
      if(value>peak){peak=value;peakIndex=index;}
      const drop=value/peak-1;
      if(drop<worst){worst=drop;found={index,peakIndex,drop,peak,value};}
    });
    return found;
  }
  function groupTrades(trades,day,actor=''){
    const groups=new Map();
    for(const trade of trades){
      if(trade.day>day||(actor&&trade.actor!==actor))continue;
      const key=[trade.day,trade.actor,trade.filed||'',trade.period||''].join('|');
      if(!groups.has(key))groups.set(key,{key,day:trade.day,actor:trade.actor,trades:[],buy:0,sell:0});
      const group=groups.get(key);group.trades.push(trade);group[trade.action]+=trade.amount;
    }
    return [...groups.values()].sort((a,b)=>b.day.localeCompare(a.day)||a.actor.localeCompare(b.actor));
  }
  return {firstTrade,drawdownMoment,groupTrades};
});
