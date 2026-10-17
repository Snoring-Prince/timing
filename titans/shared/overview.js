/* Latest filing overview. The browser and the static publisher use this same
   renderer; it describes reported positions, never infers executions or intent. */
(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.TitanOverview=factory();
})(typeof window==='object'?window:this,function(){
  'use strict';
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const isShare=h=>String(h.type||'SH').trim().toUpperCase()==='SH'&&!String(h.putCall||'').trim();
  const key=h=>h.cusip.slice(0,6)+(/\bPFD\b|PREFERRED/.test((h.class||'').toUpperCase())?'|P':'');
  const keep=new Set(['IBM','HP','NVR','USA','US','UK','AT&T','PLC','LLC','NV','SA','AG','ADR','REIT','MTN']);
  const small=new Set(['of','and','the','for','de','la']);
  function title(s){
    if(/[a-z]/.test(s))return s;
    return s.split(/\s+/).map((w,i)=>keep.has(w.replace(/[^A-Z&.]/g,''))?w
      :i&&small.has(w.toLowerCase())?w.toLowerCase():w.charAt(0)+w.slice(1).toLowerCase()).join(' ');
  }
  /* Tickers come from the investor's own price file, the same file the page
     loads. It covers current holdings only, so a name without one simply shows
     no ticker. The filter mirrors acceptPrices() in investor.js. */
  const tickerOf=t=>typeof t==='string'?t.replace(/[^A-Za-z0-9.^=-]/g,''):'';
  const isDay=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)
    &&Number.isFinite(Date.parse(d))&&new Date(Date.parse(d)).toISOString().slice(0,10)===d;
  function tickersFrom(prices){
    const out={};
    if(!prices||prices.method!=='split-adjusted-close'||!prices.series||typeof prices.series!=='object')return out;
    for(const [k,s] of Object.entries(prices.series)){
      if(!/^[A-Z0-9-]+$/.test(k)||!s||s.currency!=='USD'||typeof s.ticker!=='string'||!Array.isArray(s.values))continue;
      if(!s.values.some(o=>Array.isArray(o)&&isDay(o[0])&&Number.isFinite(o[1])&&o[1]>0))continue;
      const t=tickerOf(s.ticker);
      if(t)out[k]=t;
    }
    return out;
  }
  function positions(q,tickers){
    const groups=new Map();
    for(const h of q.holdings){
      if(!isShare(h))continue;
      if(!/^[A-Z0-9]{9}$/.test(h.cusip||'')||typeof h.name!=='string'||!h.name.trim()
          ||!Number.isFinite(h.value)||h.value<0)throw new Error('Invalid overview holding');
      const k=key(h), row=groups.get(k)||{key:k,value:0,byCusip:new Map()};
      row.value+=h.value; row.name=title(h.name); groups.set(k,row);
      row.byCusip.set(h.cusip,(row.byCusip.get(h.cusip)||0)+h.value);
    }
    // A merged group (Alphabet A+C) lists every priced class, largest first.
    return [...groups.values()].map(({byCusip,...r})=>({...r,tickers:[...new Set(
      [...byCusip].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([c])=>tickerOf(tickers[c])).filter(Boolean))]}))
      .sort((a,b)=>b.value-a.value||a.key.localeCompare(b.key));
  }
  function summarize(book,tickers={}){
    const qs=book.quarters;
    tickers=tickers&&typeof tickers==='object'?tickers:{};
    if(!Array.isArray(qs)||!qs.length)throw new Error('No filings for overview');
    for(let i=0;i<qs.length;i++){
      if(!/^\d{4}-(03-31|06-30|09-30|12-31)$/.test(qs[i].period||'')
          ||!Array.isArray(qs[i].holdings)||(i&&qs[i-1].period>=qs[i].period))
        throw new Error('Invalid or unordered overview quarters');
    }
    const cur=qs.at(-1), prev=qs.at(-2), rows=positions(cur,tickers), before=prev?positions(prev,tickers):[];
    const currentKeys=new Set(rows.map(r=>r.key)), previousKeys=new Set(before.map(r=>r.key));
    const total=rows.reduce((s,r)=>s+r.value,0);
    return {period:cur.period,filed:cur.filed||'',previous:prev?prev.period:null,stocks:rows.length,
      top:rows.slice(0,3).map(r=>({...r,weight:total?r.value/total*100:null})),
      appeared:prev?rows.filter(r=>!previousKeys.has(r.key)):[],
      absent:prev?before.filter(r=>!currentKeys.has(r.key)):[]};
  }
  const quarter=(iso,lang)=>lang==='ko'?`${iso.slice(0,4)}년 ${+iso.slice(5,7)/3}분기`
    :`Q${+iso.slice(5,7)/3} ${iso.slice(0,4)}`;
  const date=(iso,lang)=>lang==='ko'?iso.replaceAll('-','.') : iso;
  // "Apple Inc (AAPL, 22.0%)": ticker and weight share one bracket when known.
  function label(r,weight){
    const bits=[];
    if(r.tickers&&r.tickers.length)bits.push(r.tickers.map(escape).join('/'));
    if(weight)bits.push(weight);
    return escape(r.name)+(bits.length?` (${bits.join(', ')})`:'');
  }
  const weightText=w=>w===null?'':`${w>0&&w<0.1?'&lt;0.1':w.toFixed(1)}%`;
  const list=(items,lang)=>lang==='ko'||items.length<2?items.join(', ')
    :`${items.slice(0,-1).join(', ')} and ${items.at(-1)}`;
  function names(rows,lang){
    const shown=rows.slice(0,2).map(r=>label(r,'')).join(', '), rest=rows.length-2;
    return shown+(rest>0?(lang==='ko'?` 외 ${rest}종목`:` and ${rest} more`):'');
  }
  function changes(s,lang){
    if(!s.previous)return lang==='ko'?'이전 공시가 없어 보유 종목의 변화를 비교할 수 없습니다.'
      :'There is no earlier filing to compare positions with.';
    const basis=quarter(s.previous,lang);
    if(!s.appeared.length&&!s.absent.length)return lang==='ko'
      ?`${basis} 공시와 비교해 새로 나타나거나 빠진 종목은 없습니다. 기존 종목의 수량·비중 변화는 아래에서 볼 수 있습니다.`
      :`No positions appeared or disappeared compared with the ${basis} filing. Changes in existing positions’ shares and weights are shown below.`;
    const parts=[];
    if(s.appeared.length)parts.push(lang==='ko'?`새로 나타난 종목은 ${names(s.appeared,lang)}`:`Newly present: ${names(s.appeared,lang)}`);
    if(s.absent.length)parts.push(lang==='ko'?`이번 공시에서 빠진 종목은 ${names(s.absent,lang)}`:`No longer reported: ${names(s.absent,lang)}`);
    return (lang==='ko'?`${basis} 공시와 비교했습니다. `:`Compared with the ${basis} filing. `)
      +parts.join(lang==='ko'?'이며, ':'. ')+(lang==='ko'?'입니다.':'.');
  }
  function content(book,investor,tickers){
    const s=summarize(book,tickers);
    return ['en','ko'].map(lang=>{
      const ko=lang==='ko', name=escape(investor.name[lang]);
      const heading=ko?`${quarter(s.period,lang)} 보유 요약`:`${quarter(s.period,lang)} portfolio snapshot`;
      const stamp=s.filed?(ko?`${date(s.filed,lang)} 공시`:`Filed ${date(s.filed,lang)}`):(ko?'공시일 미상':'Filing date unavailable');
      const top=list(s.top.map(r=>label(r,weightText(r.weight))),lang);
      const held=ko?`${name}의 미국 상장 주식 보유 기록은 ${s.stocks}종목입니다.`
        :`${name} reports ${s.stocks} US-listed stock position${s.stocks===1?'':'s'}.`;
      const largest=top?(ko?` 보유 금액 상위 ${s.top.length}종목은 ${top}입니다.`:` The ${s.top.length===1?'largest position is':`largest ${s.top.length} positions are`} ${top}.`):'';
      return `  <div data-lang="${lang}">\n    <h2>${heading}</h2>\n    <p class="overview-date">${escape(stamp)}</p>\n    <p>${held}${largest}</p>\n    <p>${changes(s,lang)}</p>\n  </div>`;
    }).join('\n');
  }
  function section(book,investor,tickers){
    return `<section class="filing-overview" id="filing-overview">\n${content(book,investor,tickers)}\n</section>`;
  }
  return {summarize,content,section,tickersFrom};
});
