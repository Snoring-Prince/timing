(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else(root.OlympicStrategies||={}).daniel=factory();})(typeof window==='undefined'?this:window,()=>({id:'daniel',step(c,s){
  if(c.first)return;
  if(c.fear===undefined){s.known=false;return;}
  const zone=c.fear<=c.options.fear?'fear':c.fear>=c.options.greed?'greed':'middle';
  // A missing observation cannot prove a new crossing. First observed signal is eligible.
  const trigger=c.options.repeat||!s.observed||(s.known&&zone!==s.zone);
  if(trigger&&zone==='fear')c.buy(c.asset,c.initial*c.options.buy/100,'fear',{signalDay:c.signalDay,fear:c.fear});
  if(trigger&&zone==='greed')c.sell(c.asset,c.initial*c.options.sell/100,'greed',{signalDay:c.signalDay,fear:c.fear});
  s.zone=zone;s.known=true;s.observed=true;
}}));
