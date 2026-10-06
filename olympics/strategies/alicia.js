(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else(root.OlympicStrategies||={}).alicia=factory();})(typeof window==='undefined'?this:window,()=>({id:'alicia',step(c){
  for(const event of c.filings){
    const meta={signalDay:event.filed,filed:event.filed,period:event.period};
    for(const change of event.changes)if(change.ratio<1)c.trim(change.key,1-change.ratio,change.ratio===0?'exit':'reduce',meta);
    // Never start copying a stock just because an existing Berkshire holding grew.
    const buys=event.changes.filter(x=>x.increase>0&&(x.new||c.has(x.key)));
    const weights=buys.reduce((n,b)=>n+b.increase,0),budget=Math.min(c.initial*c.options.alicia/100,c.reserve());
    for(const change of buys)c.buy(change.key,budget*change.increase/weights,change.new?'new':'add',meta);
  }
}}));
