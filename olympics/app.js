(()=>{
  'use strict';
  const $=id=>document.getElementById(id),M=window.OlympicModel,IDS=M.ids;
  const HEAD={
    en:{title:'Five investing strategies, the same starting cash — Investment Olympics',desc:'Replay five investing strategies with the same initial cash: Treasury bills, Fear & Greed, monthly purchases, following public Berkshire filings, and buy-and-hold.'},
    ko:{title:'같은 목돈으로 투자 전략 5가지 비교 — 투자 올림픽',desc:'단기 국채 ETF, 공포탐욕지수, 매달 투자, 버크셔 공개 공시 따라 사기, 한 번에 투자하기. 같은 목돈으로 시작한 다섯 사람의 과거 수익률과 순위 변화를 살펴보세요.'}
  };
  const D={
    ko:{john:'존',daniel:'다니엘',samuel:'사무엘',alicia:'알리시아',emma:'엠마',amount:'준비된 목돈 (USD)',asset:'다니엘·사무엘·엠마의 ETF',start:'시작일',end:'종료일',advanced:'각자의 선택 조정하기',fear:'다니엘 · 매수 공포지수 이하',greed:'다니엘 · 매도 탐욕지수 이상',buy:'다니엘 · 한 번 매수 (%)',sell:'다니엘 · 한 번 매도 (%)',monthly:'사무엘 · 매달 매수 (%)',aliciaBudget:'알리시아 · 공시당 예산 (%)',repeat:'다니엘: 조건에 맞는 관측일마다 반복 매매',entry:'기본은 해당 공포·탐욕 구간에 들어갈 때 한 번입니다. 모든 비율은 처음 목돈을 기준으로 합니다.',apply:'이 조건으로 비교하기',pending:'조건을 바꿨어요. 비교하기를 눌러 결과에 반영하세요.',first:'처음',last:'마지막',play:'재생',pause:'일시정지',timeline:'비교 날짜',total:'총자산 = 주식 + BIL · USD · 차트에 마우스·손가락을 대거나 좌우 방향키로 날짜별 값을 볼 수 있습니다.',decisions:'이날까지 어떤 선택을 했을까?',filter:'사람별 매매 보기',all:'모두',more:'더 보기',loading:'과거 기록을 불러오고 있어요.',error:'비교에 필요한 자료를 불러오지 못했어요. 잠시 뒤 다시 열어주세요.',inputs:'금액과 비율을 확인해주세요. 공포 기준은 탐욕 기준보다 낮아야 합니다.',range:'자료 범위 안에서 서로 다른 두 거래일 이상을 골라주세요.',nav:'메인 메뉴',assets:'총자산',return:'총수익률',reserve:'대기 자금 · BIL',drop:'가장 크게 줄었던 폭',empty:'이날까지 실제로 실행된 주식 매매가 없습니다. 남은 돈은 BIL에 있습니다.',buyTrade:'매수',sellTrade:'매도',chart:'다섯 사람의 과거 총자산 변화. 좌우 방향키로 날짜별 값을 확인할 수 있습니다.'},
    en:{john:'John',daniel:'Daniel',samuel:'Samuel',alicia:'Alicia',emma:'Emma',amount:'Initial cash (USD)',asset:'Daniel, Samuel & Emma’s ETF',start:'Start',end:'End',advanced:'Adjust their decisions',fear:'Daniel · Buy when fear ≤',greed:'Daniel · Sell when greed ≥',buy:'Daniel · Buy per signal (%)',sell:'Daniel · Sell per signal (%)',monthly:'Samuel · Monthly purchase (%)',aliciaBudget:'Alicia · Budget per filing (%)',repeat:'Daniel: repeat after every qualifying observation',entry:'By default, one trade on entering a fear or greed zone. All percentages use initial cash.',apply:'Compare these decisions',pending:'Settings changed. Apply them to update the result.',first:'Start',last:'End',play:'Play',pause:'Pause',timeline:'Comparison date',total:'Total assets = equities + BIL · USD · Hover, touch, or use left/right arrow keys to inspect dates.',decisions:'Decisions up to this date',filter:'Filter person',all:'Everyone',more:'Show more',loading:'Loading historical observations…',error:'The observations needed for this comparison could not be loaded. Please try again later.',inputs:'Check cash and percentages. The fear threshold must be below the greed threshold.',range:'Choose at least two different trading days within the available history.',nav:'Main',assets:'Total assets',return:'Total return',reserve:'Waiting funds · BIL',drop:'Largest peak-to-trough drop',empty:'No equity trades have executed by this date. Remaining funds stay in BIL.',buyTrade:'Buy',sellTrade:'Sell',chart:'Historical total assets for five people. Use left and right arrow keys to inspect dates.'}
  };
  function pick(){const q=(new URLSearchParams(location.search).get('lang')||'').slice(0,2).toLowerCase();if(D[q])return q;try{const s=localStorage.getItem('dt.lang');if(D[s])return s;}catch(e){}for(const l of navigator.languages||[navigator.language||'en']){if(D[l.slice(0,2)])return l.slice(0,2);}return 'en';}
  let LANG=pick(),DATA=null,RESULT=null,INDEX=0,HOVER=0,GEOMETRY=null,TIMER=null,LIMIT=15,ERROR='loading';
  const t=k=>D[LANG][k],money=n=>new Intl.NumberFormat(LANG==='ko'?'ko-KR':'en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n),pct=n=>Math.abs(n)<.0005?'0.0%':(n>0?'+':'')+(n*100).toFixed(1)+'%';
  const tradeMoney=n=>n<.005?'< US$0.01':new Intl.NumberFormat(LANG==='ko'?'ko-KR':'en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}).format(n);
  const element=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  function paintHead(){
    const h=HEAD[LANG],set=(s,v)=>document.head.querySelector(s)?.setAttribute('content',v);
    document.title=h.title;set('meta[name="description"]',h.desc);set('meta[property="og:title"]',h.title);set('meta[property="og:description"]',h.desc);
    set('meta[property="og:locale"]',LANG==='ko'?'ko_KR':'en_US');set('meta[property="og:locale:alternate"]',LANG==='ko'?'en_US':'ko_KR');
    set('meta[property="og:image"]','https://itpaidoff.com/'+(LANG==='ko'?'og-ko.png':'og.png'));
    const self='https://itpaidoff.com/olympics/'+(new URLSearchParams(location.search).get('lang')?'?lang='+LANG:'');
    const canonical=document.head.querySelector('link[rel="canonical"]')||document.head.appendChild(document.createElement('link'));
    canonical.setAttribute('rel','canonical');canonical.setAttribute('href',self);set('meta[property="og:url"]',self);
  }
  function language(){
    document.documentElement.lang=LANG;paintHead();document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=t(e.dataset.i18n));
    document.querySelectorAll('[data-route]').forEach(e=>e.href=e.dataset.route+'?lang='+LANG);document.querySelector('nav').setAttribute('aria-label',t('nav'));
    window.LanguagePicker.mount($('language-control'),{lang:LANG,languages:window.LanguagePicker.options(Object.keys(D)),onChange:code=>{
      LANG=code;try{localStorage.setItem('dt.lang',LANG);}catch(e){}const url=new URL(location.href);url.searchParams.set('lang',LANG);history.replaceState(null,'',url);language();
    }});
    $('play').textContent=t(TIMER?'pause':'play');$('status').textContent=t(ERROR);
    range();if(RESULT){applied();render();draw();}
  }
  function range(){if(DATA)$('data-range').textContent=LANG==='ko'?'비교 가능한 기록: '+DATA.data.from+' ~ '+DATA.data.to+' · 매주 갱신 · 아직 오지 않은 날짜는 비교하지 않습니다.':'Available history: '+DATA.data.from+' – '+DATA.data.to+' · Updated weekly · No future results.';}
  function options(){const o={asset:$('asset').value,start:$('start').value,end:$('end').value,repeat:$('repeat').checked};for(const k of ['amount','fear','greed','buy','sell','monthly','alicia'])o[k]=Number($(k).value);return o;}
  function applied(){
    const o=RESULT.options,asset=o.asset==='spx'?'SPY':'QQQ';
    $('applied').textContent=LANG==='ko'?`적용된 조건 · ${money(o.amount)} · ${asset} · ${RESULT.from} ~ ${RESULT.to}. 다니엘 ${o.fear} 이하 / ${o.greed} 이상, 매수 ${o.buy}% / 매도 ${o.sell}%, ${o.repeat?'반복 매매':'구간 진입 때 한 번'}. 사무엘 매달 ${o.monthly}%. 알리시아 공시당 ${o.alicia}%.`:`Applied · ${money(o.amount)} · ${asset} · ${RESULT.from} – ${RESULT.to}. Daniel ≤${o.fear} / ≥${o.greed}, buy ${o.buy}% / sell ${o.sell}%, ${o.repeat?'repeat':'zone entry only'}. Samuel monthly ${o.monthly}%. Alicia per filing ${o.alicia}%.`;
  }
  function compare(){
    stop();if(!DATA)return;
    try{if(!$('settings').checkValidity())throw Error('inputs');RESULT=M.run(DATA,options());INDEX=RESULT.curve.length-1;HOVER=INDEX;LIMIT=15;$('timeline').max=INDEX;$('race').hidden=false;$('status').hidden=true;$('pending').hidden=true;applied();render();draw();}
    catch(e){RESULT=null;$('race').hidden=true;ERROR=['inputs','range'].includes(e.message)?e.message:'error';$('status').textContent=t(ERROR);$('status').hidden=false;}
  }
  function render(){
    if(!RESULT)return;const point=RESULT.curve[INDEX];$('timeline').value=INDEX;$('timeline').setAttribute('aria-valuetext',point.day);$('current-date').textContent=point.day;
    $('date-note').textContent=LANG==='ko'?'순위와 아래 매매 기록은 이 날짜까지입니다. 같은 총자산은 공동 순위입니다.':'Ranks and decisions below use observations up to this date. Equal total assets share a rank.';
    const cards=[];
    for(const row of M.rank(point,RESULT.options.amount)){
      const card=element('article',undefined,'runner');card.style.setProperty('--person','var(--'+row.id+')');card.dataset.actor=row.id;
      const h=element('h3');h.append(element('span',t(row.id)),element('span',LANG==='ko'?row.rank+'위':'#'+row.rank,'place'));card.append(h,element('div',t('assets'),'value-label'),element('div',money(row.value),'value'));
      const dl=element('dl');for(const [label,value,cls] of [[t('return'),pct(row.return),row.return>0?'positive':row.return<0?'negative':''],[t('reserve'),money(row.reserve),''],[t('drop'),pct(row.drop),'']])dl.append(element('dt',label),element('dd',value,cls));
      card.append(dl);cards.push(card);
    }$('ranking').replaceChildren(...cards);
    $('legend').replaceChildren(...IDS.map((id,i)=>{const s=element('span');s.style.setProperty('--person','var(--'+id+')');s.append(element('i',undefined,i===1?'':i===4?'dotted':'dashed'),element('span',t(id)));return s;}));
    $('missing').textContent=RESULT.missingFear?(LANG==='ko'?`이 비교에 공포탐욕지수 관측이 없는 거래일 ${RESULT.missingFear}일이 있어 다니엘의 신호를 만들지 않았습니다.`:`Fear & Greed observations were absent for ${RESULT.missingFear} trading days; Daniel receives no invented signal.`):'';
    log();marker();
  }
  function reason(trade){
    const k=trade.reason;
    if(k==='start')return LANG==='ko'?'첫날 목돈 전부 투자':'Invest all initial cash';
    if(k==='monthly')return LANG==='ko'?'매달 처음 목돈의 정해진 비율':'Monthly share of initial cash';
    if(k==='fear'||k==='greed')return (LANG==='ko'?'공포탐욕지수 ':'Fear & Greed ')+trade.fear+' · '+trade.signalDay+(LANG==='ko'?' 관측':' observation');
    const detail=LANG==='ko'?'공개 '+trade.filed+' · '+trade.period+' 분기':'Published '+trade.filed+' · Quarter '+trade.period;
    return (LANG==='ko'?({new:'신규 진입',add:'추가 매수',reduce:'보유 감소',exit:'전량 처분'}[k]||'공시 변화'):({new:'New holding',add:'Addition',reduce:'Reduction',exit:'Full disposal'}[k]||'Filing change'))+' · '+detail;
  }
  function log(){
    const actor=$('actor').value,day=RESULT.curve[INDEX].day,rows=RESULT.trades.filter(r=>r.day<=day&&(!actor||r.actor===actor)).reverse();
    const list=rows.slice(0,LIMIT).map(r=>{const li=element('li'),time=element('time',r.day);time.dateTime=r.day;const detail=element('div',undefined,'detail'),ticker=['spx','ndx'].includes(r.key)?(r.key==='spx'?'SPY':'QQQ'):r.key;
      detail.append(element('span',t(r.action==='buy'?'buyTrade':'sellTrade')+' · '+ticker),element('p',reason(r)));li.append(time,element('strong',t(r.actor)),detail,element('span',tradeMoney(r.amount),'cash'));return li;});
    $('log').replaceChildren(...(list.length?list:[element('li',t('empty'))]));$('more').hidden=rows.length<=LIMIT;
  }
  const DASH=['7 4','','10 4','4 3','2 4'];
  function draw(){
    if(!RESULT)return;const svg=$('chart'),W=Math.max(200,Math.round(svg.clientWidth)),H=svg.clientHeight,L=W<500?45:62,R=W-12,T=15,B=H-30,rows=RESULT.curve;
    let lo=Infinity,hi=-Infinity;for(const r of rows)for(const v of Object.values(r.values)){lo=Math.min(lo,v);hi=Math.max(hi,v);}
    const pad=Math.max((hi-lo)*.1,RESULT.options.amount*.03);lo=Math.max(0,lo-pad);hi+=pad;
    const from=Date.parse(RESULT.from),span=Date.parse(RESULT.to)-from,x=d=>L+(Date.parse(d)-from)/span*(R-L),y=v=>B-(v-lo)/(hi-lo)*(B-T),n=v=>v.toFixed(2);GEOMETRY={W,H,L,R,T,B,x,y};
    let html='';
    for(let i=0;i<4;i++){const v=lo+(hi-lo)*i/3,yy=y(v);html+=`<path class="grid" d="M${L} ${n(yy)}H${R}"/><text x="${L-7}" y="${n(yy+4)}" text-anchor="end">${new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(v)}</text>`;}
    html+=`<path class="baseline" d="M${L} ${n(y(RESULT.options.amount))}H${R}"/>`;
    const ticks=W<500?3:5;for(let i=0;i<ticks;i++){const r=rows[Math.round(i*(rows.length-1)/(ticks-1))];html+=`<text x="${n(x(r.day))}" y="${H-7}" text-anchor="${i===0?'start':i===ticks-1?'end':'middle'}">${r.day.slice(0,7).replace('-','.')}</text>`;}
    IDS.forEach((id,j)=>{const path=rows.map((r,i)=>(i?'L':'M')+n(x(r.day))+' '+n(y(r.values[id]))).join(' ');html+=`<path class="curve" style="--person:var(--${id})" stroke-dasharray="${DASH[j]}" d="${path}"/>`;});
    html+='<g id="replay-line"></g><g id="hover-line"></g>';svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('aria-label',t('chart'));svg.innerHTML=html;$('tooltip').hidden=true;marker();
  }
  function marker(){if(!RESULT||!GEOMETRY||!$('replay-line'))return;const g=GEOMETRY,x=g.x(RESULT.curve[INDEX].day);$('replay-line').innerHTML=`<path class="replay-line" d="M${x} ${g.T}V${g.B}"/>`;}
  function hover(i){
    if(!RESULT||!GEOMETRY)return;HOVER=Math.max(0,Math.min(RESULT.curve.length-1,i));const p=RESULT.curve[HOVER],g=GEOMETRY,x=g.x(p.day);
    $('hover-line').innerHTML=`<path class="crosshair" d="M${x} ${g.T}V${g.B}"/>`+IDS.map(id=>`<circle cx="${x}" cy="${g.y(p.values[id])}" r="3" fill="var(--${id})"/>`).join('');
    const tip=$('tooltip');tip.replaceChildren(element('b',p.day),...IDS.map(id=>{const row=element('div');row.append(element('span',t(id)),element('span',money(p.values[id])));return row;}));tip.hidden=false;tip.style.top='6px';tip.style.left=Math.max(4,Math.min(g.W-tip.offsetWidth-4,x+12))+'px';
  }
  function pointer(e){if(!RESULT||!GEOMETRY)return;const g=GEOMETRY,rect=$('chart').getBoundingClientRect(),fraction=Math.max(0,Math.min(1,(e.clientX-rect.left-g.L)/(g.R-g.L))),time=Date.parse(RESULT.from)+fraction*(Date.parse(RESULT.to)-Date.parse(RESULT.from));
    let best=0,distance=Infinity;RESULT.curve.forEach((r,i)=>{const d=Math.abs(Date.parse(r.day)-time);if(d<distance){distance=d;best=i;}});hover(best);}
  function stop(){if(TIMER)clearInterval(TIMER);TIMER=null;$('play').textContent=t('play');}
  function seek(i){if(!RESULT)return;INDEX=Math.max(0,Math.min(RESULT.curve.length-1,i));LIMIT=15;render();}
  $('settings').addEventListener('submit',e=>{e.preventDefault();compare();});
  $('settings').addEventListener('input',()=>{stop();$('pending').hidden=!RESULT;});
  $('timeline').addEventListener('input',()=>{stop();seek(Number($('timeline').value));});
  $('first').addEventListener('click',()=>{stop();seek(0);});$('last').addEventListener('click',()=>{stop();seek(RESULT.curve.length-1);});
  $('play').addEventListener('click',()=>{if(!RESULT)return;if(TIMER){stop();return;}if(INDEX===RESULT.curve.length-1)seek(0);$('play').textContent=t('pause');TIMER=setInterval(()=>{seek(INDEX+Math.max(1,Math.ceil(RESULT.curve.length/140)));if(INDEX===RESULT.curve.length-1)stop();},180);});
  $('actor').addEventListener('change',()=>{LIMIT=15;log();});$('more').addEventListener('click',()=>{LIMIT+=15;log();});
  $('chart').addEventListener('pointermove',pointer);$('chart').addEventListener('pointerdown',pointer);
  function hideTip(){$('tooltip').hidden=true;if($('hover-line'))$('hover-line').innerHTML='';}
  $('chart').addEventListener('pointerleave',hideTip);$('chart').addEventListener('blur',hideTip);
  $('chart').addEventListener('keydown',e=>{if(!RESULT)return;if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();hover(e.key==='Home'?0:e.key==='End'?RESULT.curve.length-1:HOVER+(e.key==='ArrowLeft'?-1:1));}else if(e.key==='Escape')hideTip();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  if(typeof ResizeObserver==='function')new ResizeObserver(draw).observe($('chart'));else window.addEventListener('resize',draw);
  language();
  fetch('/data/olympics/race.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json();}).then(raw=>{
    DATA=M.prepare(raw);for(const id of ['start','end']){$(id).min=raw.from;$(id).max=raw.to;$(id).value=raw[id==='start'?'from':'to'];}
    $('apply').disabled=false;range();compare();
  }).catch(()=>{ERROR='error';$('status').textContent=t(ERROR);$('status').hidden=false;$('race').hidden=true;$('apply').disabled=true;});
})();
