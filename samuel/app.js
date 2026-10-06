(()=>{
  'use strict';
  const $=id=>document.getElementById(id),M=window.SamuelModel;
  const HEAD={
    en:{title:'Lump sum vs. phased investing in SPY and QQQ — Samuel’s decision',desc:'Compare investing a lump sum with spreading the same cash over 3, 6 or 12 months. Explore historical SPY and QQQ portfolio values, drawdowns and monthly starting points.'},
    ko:{title:'S&P500·나스닥100 일시금과 분할 투자 비교 — 사무엘의 결정',desc:'같은 목돈을 한 번에 투자할까, 3·6·12개월로 나눠 투자할까? SPY·QQQ의 과거 총자산 변화와 낙폭을 여러 시작 시점에서 비교해보세요.'}
  };
  const D={
    ko:{asset:'투자 대상',amount:'준비된 목돈 (USD)',start:'투자 시작월',months:'나눠 넣는 기간',years:'비교할 기간',reserve:'기다리는 돈은',m3:'3개월',m6:'6개월',m12:'12개월',y1:'1년',y3:'3년',y5:'5년',y10:'10년',lump:'한 번에 넣기',split:'나눠 넣기',return:'총수익률',drawdown:'가장 크게 줄었던 폭',totalAssets:'주식 ETF + 대기 자금(BIL) · USD',higher:'마지막에 돈이 더 남았던 쪽',loading:'과거 일별 자료를 불러오고 있어요.',error:'자료를 불러오지 못했어요. 잠시 뒤 다시 열어주세요.',inputs:'금액·시작월을 확인해주세요.',range:'두 ETF의 자료가 겹치고 선택한 기간이 모두 끝난 시작월만 비교할 수 있어요. 아래 자료 범위 안의 시작월을 선택하고, 필요하면 비교 기간을 줄여주세요.',nav:'메인 메뉴',chart:'한 번에 넣기와 나눠 넣기의 과거 총자산 변화. 좌우 방향키로 날짜별 값을 확인할 수 있습니다.'},
    en:{asset:'Investment',amount:'Initial cash (USD)',start:'Starting month',months:'Phase-in period',years:'Comparison horizon',reserve:'While waiting',m3:'3 months',m6:'6 months',m12:'12 months',y1:'1 year',y3:'3 years',y5:'5 years',y10:'10 years',lump:'All at once',split:'In stages',return:'Total return',drawdown:'Largest peak-to-trough drop',totalAssets:'Equity ETF + waiting funds (BIL) · USD',higher:'Which path ended with more?',loading:'Loading daily historical prices…',error:'The price history could not be loaded. Please try again later.',inputs:'Check the amount and starting month.',range:'Both ETF histories must overlap and cover the full selected horizon. Choose a starting month within the range below and shorten the horizon if needed.',nav:'Main',chart:'Historical total assets for lump-sum and phased investing. Use left and right arrow keys to inspect dates.'}
  };
  function pick(){const q=(new URLSearchParams(location.search).get('lang')||'').slice(0,2).toLowerCase();if(D[q])return q;try{const s=localStorage.getItem('dt.lang');if(D[s])return s;}catch(e){}for(const language of navigator.languages||[navigator.language||'en']){const code=language.slice(0,2).toLowerCase();if(D[code])return code;}return 'en';}
  let LANG=pick(),DATA=null,RESULT=null,SAMPLE=[],SAMPLE_KEY='',GEOMETRY=null,HOVER=0,TIMER=null,FAIL=false;
  const t=key=>D[LANG][key],money=n=>new Intl.NumberFormat(LANG==='ko'?'ko-KR':'en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n),percent=n=>(n>0?'+':'')+(n*100).toFixed(1)+'%';
  function paintHead(){
    const h=HEAD[LANG],set=(selector,value)=>document.head.querySelector(selector)?.setAttribute('content',value);
    document.title=h.title;set('meta[name="description"]',h.desc);set('meta[property="og:title"]',h.title);set('meta[property="og:description"]',h.desc);
    set('meta[property="og:locale"]',LANG==='ko'?'ko_KR':'en_US');set('meta[property="og:locale:alternate"]',LANG==='ko'?'en_US':'ko_KR');
    set('meta[property="og:image"]','https://itpaidoff.com/'+(LANG==='ko'?'og-ko.png':'og.png'));
    const self='https://itpaidoff.com/samuel/'+(new URLSearchParams(location.search).get('lang')?'?lang='+LANG:'');
    const canonical=document.head.querySelector('link[rel="canonical"]')||document.head.appendChild(document.createElement('link'));
    canonical.setAttribute('rel','canonical');canonical.setAttribute('href',self);set('meta[property="og:url"]',self);
  }
  function paintLanguage(){
    document.documentElement.lang=LANG;paintHead();
    document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=t(e.dataset.i18n));
    document.querySelectorAll('[data-route]').forEach(a=>a.href=a.dataset.route+'?lang='+LANG);
    document.querySelector('nav').setAttribute('aria-label',t('nav'));
    window.LanguagePicker.mount($('language-control'),{lang:LANG,languages:window.LanguagePicker.options(Object.keys(D)),onChange:code=>{
      LANG=code;try{localStorage.setItem('dt.lang',LANG);}catch(e){}
      const url=new URL(location.href);url.searchParams.set('lang',LANG);try{history.replaceState(null,'',url);}catch(e){}
      paintLanguage();
    }});paintDataRange();render();
  }
  function options(){return {amount:Number($('amount').value),months:Number($('months').value),years:Number($('years').value)};}
  function status(key){$('status').textContent=t(key);$('status').hidden=false;$('comparison').hidden=true;$('samples').hidden=true;$('samples-heading').hidden=true;RESULT=null;}
  function render(){
    if(!DATA){status(FAIL?'error':'loading');return;}
    try{
      if(!$('settings').checkValidity())throw Error($('start').validity.rangeUnderflow||$('start').validity.rangeOverflow?'range':'inputs');
      const rows=M.paired(DATA,$('asset').value),o=options();RESULT=M.simulate(rows,$('start').value,o);
      const key=JSON.stringify([$('asset').value,o.months,o.years]);
      if(key!==SAMPLE_KEY){SAMPLE=M.cohorts(rows,o);SAMPLE_KEY=key;}
      $('status').hidden=true;$('comparison').hidden=false;$('samples').hidden=false;$('samples-heading').hidden=false;
      $('value-lump').textContent=money(RESULT.lump);$('value-split').textContent=money(RESULT.split);
      $('split-label').textContent=LANG==='ko'?o.months+'개월로 나눠 넣기':`Phased over ${o.months} months`;
      for(const [id,value] of [['return-lump',RESULT.returnL],['return-split',RESULT.returnS],['drawdown-lump',RESULT.mddL],['drawdown-split',RESULT.mddS]]){
        $(id).textContent=percent(value);$(id).className=value<0?'negative':value>0?'positive':'';
      }
      $('dates').textContent=RESULT.from.replaceAll('-','.')+' – '+RESULT.to.replaceAll('-','.');
      $('reserve-note').textContent=LANG==='ko'?`처음 목돈을 ${o.months}등분합니다. 기다리는 동안 생긴 BIL 수익도 각 몫과 함께 주식으로 옮깁니다.`:`Initial cash is divided into ${o.months} equal portions. Each portion’s BIL return moves into equities with it.`;
      draw();paintSamples();
    }catch(e){status(e.message==='inputs'?'inputs':e.message==='range'?'range':'error');}
  }
  function paintSamples(){
    const s=M.summarize(SAMPLE);if(!s){$('samples').hidden=true;$('samples-heading').hidden=true;return;}
    const o=options(),share=n=>(n/s.n*100).toFixed(1)+'%';
    $('bar-lump').style.width=share(s.lump);$('bar-split').style.width=share(s.split);
    $('sample-lump').textContent=share(s.lump);$('sample-split').textContent=share(s.split);
    $('median-lump').textContent=(LANG==='ko'?'총수익률 중앙값 ':'Median total return ')+percent(s.medianL);
    $('median-split').textContent=(LANG==='ko'?'총수익률 중앙값 ':'Median total return ')+percent(s.medianS);
    $('sample-range').textContent=SAMPLE[0].month+' – '+SAMPLE.at(-1).month;
    $('sample-note').textContent=LANG==='ko'?`${s.n}개 시작월 · 한 번에 ${s.lump}회 / 나눠서 ${s.split}회 / 같은 결과 ${s.ties}회. 모두 ${o.years}년 뒤 총자산으로 비교합니다.`:`${s.n} starting months · Lump sum ${s.lump} / phased ${s.split} / ties ${s.ties}. Each comparison ends after ${o.years} year${o.years===1?'':'s'}.`;
  }
  function draw(){
    if(!RESULT||$('comparison').hidden)return;
    const svg=$('chart'),W=Math.max(200,Math.round(svg.clientWidth)),H=svg.clientHeight,L=W<500?46:64,R=W-12,T=16,B=H-31;
    const all=RESULT.curve.flatMap(r=>[r.lump,r.split]),low=Math.min(...all),high=Math.max(...all),pad=Math.max((high-low)*.1,RESULT.amount*.03),lo=Math.max(0,low-pad),hi=high+pad;
    const start=Date.parse(RESULT.from),span=Date.parse(RESULT.to)-start;
    const x=d=>L+(Date.parse(d)-start)/span*(R-L),y=v=>B-(v-lo)/(hi-lo)*(B-T),n=v=>v.toFixed(2);
    GEOMETRY={W,H,L,R,T,B,x,y};
    let content='';
    for(let i=0;i<4;i++){const v=lo+(hi-lo)*i/3,yy=y(v);content+=`<path class="grid" d="M${L} ${n(yy)}H${R}"/><text x="${L-7}" y="${n(yy+4)}" text-anchor="end">${new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(v)}</text>`;}
    content+=`<path class="baseline" d="M${L} ${n(y(RESULT.amount))}H${R}"/>`;
    const ticks=W<500?3:5;
    for(let i=0;i<ticks;i++){const point=RESULT.curve[Math.round(i*(RESULT.curve.length-1)/(ticks-1))],xx=x(point.day);content+=`<text x="${n(xx)}" y="${H-8}" text-anchor="${i===0?'start':i===ticks-1?'end':'middle'}">${point.day.slice(0,7).replace('-','.')}</text>`;}
    for(const key of ['lump','split']){
      const path=RESULT.curve.map((r,i)=>(i?'L':'M')+n(x(r.day))+' '+n(y(r[key]))).join(' ');
      content+=`<path class="curve ${key}" d="${path}"/>`;
    }
    content+='<g id="hover-line" hidden></g>';
    svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('aria-label',t('chart'));svg.innerHTML=content;$('tooltip').hidden=true;
  }
  function hover(index){
    if(!RESULT||!GEOMETRY)return;HOVER=Math.max(0,Math.min(RESULT.curve.length-1,index));
    const r=RESULT.curve[HOVER],g=GEOMETRY,x=g.x(r.day),line=$('hover-line');line.removeAttribute('hidden');
    line.innerHTML=`<path class="crosshair" d="M${x} ${g.T}V${g.B}"/><circle cx="${x}" cy="${g.y(r.lump)}" r="3" fill="var(--lump)"/><circle cx="${x}" cy="${g.y(r.split)}" r="3" fill="var(--split)"/>`;
    const tip=$('tooltip');tip.replaceChildren();const date=document.createElement('b');date.textContent=r.day;tip.appendChild(date);
    for(const [label,value] of [[t('lump'),r.lump],[t('split'),r.split]]){const row=document.createElement('div'),name=document.createElement('span'),number=document.createElement('span');name.textContent=label;number.textContent=money(value);row.append(name,number);tip.appendChild(row);}
    tip.hidden=false;tip.style.top='8px';tip.style.left=Math.max(4,Math.min(g.W-tip.offsetWidth-4,x+12))+'px';
  }
  function inspectPointer(event){
    if(!RESULT||!GEOMETRY)return;const rect=$('chart').getBoundingClientRect(),fraction=Math.max(0,Math.min(1,(event.clientX-rect.left-GEOMETRY.L)/(GEOMETRY.R-GEOMETRY.L)));
    const time=Date.parse(RESULT.from)+fraction*(Date.parse(RESULT.to)-Date.parse(RESULT.from));
    let i=M.lowerBound(RESULT.curve.map(r=>[r.day]),new Date(time).toISOString().slice(0,10));
    if(i>0&&i<RESULT.curve.length&&Math.abs(Date.parse(RESULT.curve[i-1].day)-time)<Math.abs(Date.parse(RESULT.curve[i].day)-time))i--;hover(i);
  }
  $('chart').addEventListener('pointermove',inspectPointer);
  $('chart').addEventListener('pointerdown',inspectPointer);
  $('chart').addEventListener('pointerleave',()=>{$('tooltip').hidden=true;$('hover-line')?.setAttribute('hidden','');});
  $('chart').addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)&&RESULT){event.preventDefault();hover(event.key==='Home'?0:event.key==='End'?RESULT.curve.length-1:HOVER+(event.key==='ArrowLeft'?-1:1));}});
  $('settings').addEventListener('submit',event=>event.preventDefault());
  $('settings').addEventListener('input',()=>{clearTimeout(TIMER);TIMER=setTimeout(render,150);});
  function paintDataRange(){
    if(!DATA)return;
    const rows=M.paired(DATA,$('asset').value),from=rows[0][0],to=rows.at(-1)[0];
    $('start').min=from.slice(0,7);$('start').max=to.slice(0,7);
    $('data-range').textContent=LANG==='ko'?`주식 ETF·BIL 공통 일별 자료 ${from} – ${to} · 매주 갱신`:`Shared equity ETF / BIL daily history ${from} – ${to} · Refreshed weekly`;
  }
  $('asset').addEventListener('change',paintDataRange);
  paintLanguage();
  if(typeof ResizeObserver==='function')new ResizeObserver(draw).observe($('chart'));else window.addEventListener('resize',draw);
  fetch('/data/samuel/prices.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json();}).then(data=>{
    const rows=M.paired(data,$('asset').value);M.paired(data,'spx');M.paired(data,'ndx');DATA=data;
    paintDataRange();
    $('start').value=M.addMonths(rows.at(-1)[0],-37).slice(0,7);render();
  }).catch(()=>{FAIL=true;DATA=null;status('error');});
})();
