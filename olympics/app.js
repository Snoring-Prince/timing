(()=>{
  'use strict';
  const $=id=>document.getElementById(id),M=window.OlympicModel,P=window.OlympicPresentation,IDS=M.ids;
  const HEAD={
    en:{title:'Five investing strategies, the same starting cash — Investment Olympics',desc:'Replay five investing strategies with the same initial cash: Treasury bills, Fear & Greed, monthly purchases, following public Berkshire filings, and buy-and-hold.'},
    ko:{title:'같은 목돈으로 투자 전략 5가지 비교 — 투자 올림픽',desc:'단기 국채 ETF, 공포탐욕지수, 매달 투자, 버크셔 공개 공시 따라 사기, 한 번에 투자하기. 같은 목돈으로 시작한 다섯 사람의 과거 수익률과 순위 변화를 살펴보세요.'}
  };
  const D={
    ko:{john:'존',daniel:'다니엘',samuel:'사무엘',alicia:'알리시아',emma:'엠마',amount:'준비된 목돈 (USD)',asset:'다니엘·사무엘·엠마의 ETF',start:'시작일',end:'종료일',advanced:'각자의 선택 조정하기',fear:'다니엘 · 매수 공포지수 이하',greed:'다니엘 · 매도 탐욕지수 이상',buy:'다니엘 · 한 번 매수 (%)',sell:'다니엘 · 한 번 매도 (%)',monthly:'사무엘 · 매달 매수 (%)',aliciaBudget:'알리시아 · 공시당 예산 (%)',repeat:'다니엘: 조건에 맞는 관측일마다 반복 매매',entry:'기본은 해당 공포·탐욕 구간에 들어갈 때 한 번입니다. 모든 비율은 처음 목돈을 기준으로 합니다.',apply:'이 조건으로 비교하기',pending:'조건을 바꿨어요. 비교하기를 눌러 결과에 반영하세요.',first:'처음',last:'마지막',play:'재생',pause:'일시정지',timeline:'비교 날짜',total:'총자산 = 주식 + BIL · USD · 차트에 마우스·손가락을 대거나 좌우 방향키로 날짜별 값을 볼 수 있습니다.',decisions:'이날까지 어떤 선택을 했을까?',filter:'사람별 매매 보기',all:'모두',more:'더 보기',loading:'과거 기록을 불러오고 있어요.',error:'비교에 필요한 자료를 불러오지 못했어요. 잠시 뒤 다시 열어주세요.',inputs:'금액과 비율을 확인해주세요. 공포 기준은 탐욕 기준보다 낮아야 합니다.',range:'자료 범위 안에서 서로 다른 두 거래일 이상을 골라주세요.',nav:'메인 메뉴',assets:'총자산',return:'총수익률',reserve:'대기 자금 · BIL',drop:'가장 크게 줄었던 폭',empty:'이날까지 실제로 실행된 주식 매매가 없습니다. 남은 돈은 BIL에 있습니다.',buyTrade:'매수',sellTrade:'매도',chart:'다섯 사람의 과거 총자산 변화. 좌우 방향키로 날짜별 값을 확인할 수 있습니다.'},
    en:{john:'John',daniel:'Daniel',samuel:'Samuel',alicia:'Alicia',emma:'Emma',amount:'Initial cash (USD)',asset:'Daniel, Samuel & Emma’s ETF',start:'Start',end:'End',advanced:'Adjust their decisions',fear:'Daniel · Buy when fear ≤',greed:'Daniel · Sell when greed ≥',buy:'Daniel · Buy per signal (%)',sell:'Daniel · Sell per signal (%)',monthly:'Samuel · Monthly purchase (%)',aliciaBudget:'Alicia · Budget per filing (%)',repeat:'Daniel: repeat after every qualifying observation',entry:'By default, one trade on entering a fear or greed zone. All percentages use initial cash.',apply:'Compare these decisions',pending:'Settings changed. Apply them to update the result.',first:'Start',last:'End',play:'Play',pause:'Pause',timeline:'Comparison date',total:'Total assets = equities + BIL · USD · Hover, touch, or use left/right arrow keys to inspect dates.',decisions:'Decisions up to this date',filter:'Filter person',all:'Everyone',more:'Show more',loading:'Loading historical observations…',error:'The observations needed for this comparison could not be loaded. Please try again later.',inputs:'Check cash and percentages. The fear threshold must be below the greed threshold.',range:'Choose at least two different trading days within the available history.',nav:'Main',assets:'Total assets',return:'Total return',reserve:'Waiting funds · BIL',drop:'Largest peak-to-trough drop',empty:'No equity trades have executed by this date. Remaining funds stay in BIL.',buyTrade:'Buy',sellTrade:'Sell',chart:'Historical total assets for five people. Use left and right arrow keys to inspect dates.'}
  };
  const METHODS={
    ko:{
      john:()=> '목돈 전부를 단기 국채 ETF인 BIL에 넣고 계속 보유합니다.',
      daniel:(o,asset)=>`공포 ${o.fear} 이하에 ${asset} ${o.buy}% 매수, 탐욕 ${o.greed} 이상에 ${o.sell}% 매도. ${o.repeat?'조건에 맞는 관측일마다':'구간 진입 때 한 번'} 신호를 확인하고 다음 거래일에 실행합니다.`,
      samuel:(o,asset)=>`첫날부터 매달 목돈의 ${o.monthly}%씩 ${asset}를 사고, 팔지 않고 계속 보유합니다.`,
      alicia:o=>`버크셔의 신규 종목부터 따라 삽니다. 공시당 목돈의 ${o.alicia}%를 나눠 사고, 보유 종목의 추가 매수·비례 매도도 공개 후 따라갑니다.`,
      emma:(o,asset)=>`첫날 목돈 전부로 ${asset}를 사고, 팔지 않고 계속 보유합니다.`
    },
    en:{
      john:()=> 'Invests all initial cash in BIL, a Treasury bill ETF, and holds it.',
      daniel:(o,asset)=>`Buys ${o.buy}% in ${asset} at fear ≤${o.fear}; sells ${o.sell}% at greed ≥${o.greed}. Signals ${o.repeat?'after every qualifying observation':'once on zone entry'}; trades the next trading day.`,
      samuel:(o,asset)=>`Buys ${o.monthly}% of initial cash in ${asset} from day one, then monthly. Holds without selling.`,
      alicia:o=>`Starts with new Berkshire holdings. Splits ${o.alicia}% of initial cash per filing across purchases, then follows additions and proportional sales after disclosure.`,
      emma:(o,asset)=>`Invests all initial cash in ${asset} on day one, then holds without selling.`
    }
  };
  function pick(){const q=(new URLSearchParams(location.search).get('lang')||'').slice(0,2).toLowerCase();if(D[q])return q;try{const s=localStorage.getItem('dt.lang');if(D[s])return s;}catch(e){}for(const l of navigator.languages||[navigator.language||'en']){if(D[l.slice(0,2)])return l.slice(0,2);}return 'en';}
  const SHORT={ko:{john:'단기국채에 맡기기',daniel:'공포에 나눠 매수',samuel:'매달 나눠 매수',alicia:'공개된 신규 종목 따라 사기',emma:'첫날 전액 매수'},en:{john:'Hold Treasury bills',daniel:'Buy in extreme fear',samuel:'Buy every month',alicia:'Follow new public holdings',emma:'Buy all on day one'}};
  let LANG=pick(),DATA=null,RESULT=null,INDEX=0,HOVER=0,GEOMETRY=null,TIMER=null,LIMIT=6,ERROR='loading',FOCUS='',EVENT=null,MOMENTS=[],PERSON='',REVEALED=false,COMPARING=false;
  const t=k=>D[LANG][k],money=n=>new Intl.NumberFormat(LANG==='ko'?'ko-KR':'en-US',{style:'currency',currency:'USD',currencyDisplay:'narrowSymbol',maximumFractionDigits:0}).format(n),pct=n=>Math.abs(n)<.0005?'0.0%':(n>0?'+':'')+(n*100).toFixed(1)+'%';
  const tradeMoney=n=>n>0&&n<.005?'< $0.01':new Intl.NumberFormat(LANG==='ko'?'ko-KR':'en-US',{style:'currency',currency:'USD',currencyDisplay:'narrowSymbol',minimumFractionDigits:2,maximumFractionDigits:2}).format(n);
  const signedMoney=n=>(Math.abs(n)<.005?'':n<0?'−':'+')+new Intl.NumberFormat(LANG==='ko'?'ko-KR':'en-US',{style:'currency',currency:'USD',currencyDisplay:'narrowSymbol',maximumFractionDigits:2}).format(Math.abs(n)<.005?0:Math.abs(n));
  const dropText=n=>n<0&&Math.abs(n)<.001?(LANG==='ko'?'0.1% 미만':'<0.1%'):pct(n);
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
    range();story();if(RESULT){applied();personal();render();legend();moments();draw();eventNote();}
  }
  function range(){if(DATA)$('data-range').textContent=LANG==='ko'?'비교 가능한 기록: '+DATA.data.from+' ~ '+DATA.data.to+' · 매주 갱신 · 아직 오지 않은 날짜는 비교하지 않습니다.':'Available history: '+DATA.data.from+' – '+DATA.data.to+' · Updated weekly · No future results.';}
  function options(){const o={asset:$('asset').value,start:$('start').value,end:$('end').value,repeat:$('repeat').checked};for(const k of ['amount','fear','greed','buy','sell','monthly','alicia'])o[k]=Number($(k).value);return o;}
  function applied(){
    const o=RESULT.options,asset=o.asset==='spx'?'SPY':'QQQ';
    $('applied').textContent=LANG==='ko'?`각자 ${money(o.amount)}에서 출발 · ${RESULT.from} ~ ${RESULT.to} · USD · 지수 투자자는 ${asset}`:`Starting with ${money(o.amount)} each · ${RESULT.from} – ${RESULT.to} · USD · Index investors use ${asset}`;
  }
  function compare(){
    stop();if(!DATA)return;
    try{if(!$('settings').checkValidity())throw Error('inputs');RESULT=M.run(DATA,options());INDEX=RESULT.curve.length-1;HOVER=INDEX;LIMIT=6;EVENT=null;$('timeline').max=INDEX;$('race').hidden=!COMPARING;$('status').hidden=true;$('pending').hidden=true;applied();story();personal();render();legend();moments();draw();eventNote();$('skip-story').disabled=false;$('reveal-result').disabled=false;}
    catch(e){RESULT=null;$('race').hidden=true;$('personal-result').hidden=true;$('applied').textContent='';$('skip-story').disabled=true;$('reveal-result').disabled=true;story();ERROR=['inputs','range'].includes(e.message)?e.message:'error';$('status').textContent=t(ERROR);$('status').hidden=false;}
  }
  function visit(id){$(id).scrollIntoView({block:'start'});$(id).focus({preventScroll:true});}
  function story(){
    $('character-story').hidden=!PERSON;
    for(const b of document.querySelectorAll('[data-person]'))b.setAttribute('aria-pressed',String(b.dataset.person===PERSON));
    for(const a of document.querySelectorAll('[data-story]'))a.hidden=a.dataset.story!==PERSON;
    $('story-rule').textContent=PERSON&&RESULT?(LANG==='ko'?'이번 비교에서 따르는 규칙: ':'Rules used in this comparison: ')+METHODS[LANG][PERSON](RESULT.options,RESULT.options.asset==='spx'?'SPY':'QQQ'):'';
  }
  function personal(){
    $('personal-result').hidden=!(PERSON&&REVEALED&&RESULT);if($('personal-result').hidden)return;
    const row=M.rank(RESULT.curve.at(-1),RESULT.options.amount).find(r=>r.id===PERSON),low=P.drawdownMoment(RESULT,PERSON);
    $('personal-result').style.setProperty('--person','var(--'+PERSON+')');
    $('personal-heading').textContent=LANG==='ko'?t(PERSON)+'의 선택, 결과는 어땠을까요?':t(PERSON)+'’s choice: how did it turn out?';
    $('personal-period').textContent=RESULT.from+' ~ '+RESULT.to+' · USD · '+(LANG==='ko'?'배당 재투자 가정':'Distributions reinvested');
    const fields=LANG==='ko'?['처음 목돈','마지막 총자산','총수익률','투자 손익']:['Initial cash','Final total assets','Total return','Gain / loss'];
    $('personal-numbers').replaceChildren(...[money(RESULT.options.amount),money(row.value),pct(row.return),signedMoney(row.value-RESULT.options.amount)].map((value,i)=>{const d=element('div');d.append(element('span',fields[i]),element('strong',value));return d;}));
    $('personal-hardship').textContent=low?(LANG==='ko'?
      `결과에 도달하기까지, 총자산은 ${RESULT.curve[low.peakIndex].day}의 ${money(low.peak)}에서 ${RESULT.curve[low.index].day}의 ${money(low.value)}로 떨어지기도 했습니다. 고점 대비 가장 큰 하락폭은 ${dropText(low.drop).replace('-','')}${Math.abs(low.drop)<.001?'이었습니다':'였습니다'}.`:
      `Along the way, total assets fell from ${money(low.peak)} on ${RESULT.curve[low.peakIndex].day} to ${money(low.value)} on ${RESULT.curve[low.index].day}. The largest decline from a previous high was ${dropText(low.drop).replace('-','')}.`):
      (LANG==='ko'?'이 비교 기간에는 이전 고점보다 총자산이 낮아진 날이 없었습니다. 다른 기간에서도 같다는 뜻은 아닙니다.':'No observation fell below a previous high in this period. Other periods can be different.');
  }
  function comparisonNote(point){
    const rows=M.rank(point,RESULT.options.amount),leaders=rows.filter(r=>r.rank===1).map(r=>t(r.id)).join(' · '),gap=P.comparisonGap(rows,PERSON);
    let text=LANG==='ko'?`${RESULT.from} ~ ${point.day}, 총자산이 가장 큰 사람: ${leaders}.`:`${RESULT.from} – ${point.day}: highest total assets — ${leaders}.`;
    if(gap){const amount=Math.abs(gap.amount),points=Math.abs(gap.points),pp=points>0&&points<.1?(LANG==='ko'?'0.1%p 미만':'less than 0.1 percentage points'):points.toFixed(1)+(LANG==='ko'?'%p':' percentage points');
      text+=LANG==='ko'?` 내가 고른 ${t(PERSON)}의 총자산은 ${t(gap.reference.id)}보다 ${tradeMoney(amount)} ${gap.amount>0?'많고':'적고'}, 수익률은 ${pp} ${gap.amount>0?'높습니다':'낮습니다'}.`:
        ` Your choice, ${t(PERSON)}, has ${tradeMoney(amount)} ${gap.amount>0?'more':'less'} than ${t(gap.reference.id)}, with a return ${pp} ${gap.amount>0?'higher':'lower'}.`;
    }
    text+=LANG==='ko'?' 기간을 바꾸면 결과도 달라질 수 있어요.':'Results can change with the period.';
    $('comparison-lead').textContent=text;
  }
  function showComparison(){
    if(!RESULT)return;stop();COMPARING=true;EVENT=null;FOCUS='';$('actor').value='';$('race').hidden=false;seek(RESULT.curve.length-1);legend();draw();visit('comparison-lead');
  }
  for(const b of document.querySelectorAll('[data-person]'))b.addEventListener('click',()=>{
    stop();PERSON=b.dataset.person;REVEALED=false;COMPARING=false;$('race').hidden=true;$('personal-result').hidden=true;story();
    const h=document.querySelector('[data-story="'+PERSON+'"] h2');h.scrollIntoView({block:'start'});h.focus({preventScroll:true});
  });
  $('reveal-result').addEventListener('click',()=>{if(!RESULT)return;stop();REVEALED=true;COMPARING=false;$('race').hidden=true;personal();visit('personal-heading');});
  $('compare-people').addEventListener('click',showComparison);$('skip-story').addEventListener('click',showComparison);
  $('choose-again').addEventListener('click',()=>{stop();visit('character-heading');});
  function render(){
    if(!RESULT)return;const point=RESULT.curve[INDEX];$('timeline').value=INDEX;$('timeline').setAttribute('aria-valuetext',point.day);$('current-date').textContent=point.day;
    $('score-date').textContent=point.day+(LANG==='ko'?' 기준':' · selected date');
    $('date-note').textContent=LANG==='ko'?'선택한 날짜까지의 결과입니다. 이름을 누르면 그 사람의 선과 거래에 집중할 수 있어요.':'Results through the selected date. Choose a name to focus on their path and trades.';
    const cards=[],expanded=new Set([...$('ranking').querySelectorAll('.runner[open]')].map(e=>e.dataset.actor));
    for(const row of M.rank(point,RESULT.options.amount)){
      const card=element('details',undefined,'runner');card.style.setProperty('--person','var(--'+row.id+')');card.dataset.actor=row.id;card.open=expanded.has(row.id);
      const summary=element('summary'),who=element('span',undefined,'runner-who'),name=element('strong',t(row.id));
      who.append(element('span',LANG==='ko'?row.rank+'위':'#'+row.rank,'place'),name,element('span',SHORT[LANG][row.id],'short-strategy'));
      const value=element('span',undefined,'runner-value');value.append(element('span',t('assets'),'sr-only'),element('strong',money(row.value)),element('span',t('return'),'sr-only'),element('span',pct(row.return),row.return>0?'positive':row.return<0?'negative':''));
      const decline=element('span',undefined,'runner-drop');decline.append(element('span',t('drop'),'sr-only'),element('span',dropText(row.drop)),element('span','⌄','row-chevron'));summary.append(who,value,decline);
      const facts=point.facts[row.id],detail=element('div',undefined,'runner-detail');
      detail.append(element('p',METHODS[LANG][row.id](RESULT.options,RESULT.options.asset==='spx'?'SPY':'QQQ'),'strategy-description'));
      if(row.id==='samuel')detail.append(element('p',LANG==='ko'?`매달 기준 금액 ${money(RESULT.options.amount*RESULT.options.monthly/100)} · 남은 자금까지만 투자하며 외부 입금은 없어요.`:`Monthly target ${money(RESULT.options.amount*RESULT.options.monthly/100)} · Capped by remaining funds, with no new deposits.`));
      detail.append(element('p',LANG==='ko'?`종목별 매수 ${facts.buys}건 · 매도 ${facts.sells}건`:`Stock purchases: ${facts.buys} · Sales: ${facts.sells}`));
      const gains=element('dl');
      gains.append(element('dt',LANG==='ko'?'주식에 넣지 않은 돈 · BIL':'Funds outside equities · BIL'),element('dd',money(row.reserve)));
      for(const [label,value] of [[LANG==='ko'?'주식 손익':'Equity gain/loss',facts.stockGain],[LANG==='ko'?'단기국채 ETF 손익':'Treasury bill ETF gain/loss',facts.reserveGain]])gains.append(element('dt',label),element('dd',signedMoney(value),Math.abs(value)<.005?'':value<0?'negative':'positive'));
      detail.append(gains,element('p',LANG==='ko'?'매도한 주식과 보유 중인 주식의 손익을 함께 포함해요.':'Includes realized and unrealized equity gains/losses.'));
      if(row.id==='alicia')detail.append(element('p',LANG==='ko'?'시작 후 공개된 신규 종목부터 따라간 결과이며, 버크셔 전체의 수익률은 아니에요.':'This follows newly disclosed positions after the start, not Berkshire’s whole portfolio.'));
      if(row.id==='daniel'&&!point.greedObserved)detail.append(element('p',LANG==='ko'?'이날까지 확인한 매도 신호는 없어요.':'No observed sell signal through this date.'));
      const focus=element('button',LANG==='ko'?'이 사람의 선택 따라가기 →':'Follow this person’s choices →');focus.type='button';focus.addEventListener('click',()=>{stop();setFocus(row.id);$('explorer').scrollIntoView({block:'start'});$('explorer-heading').focus({preventScroll:true});});detail.append(focus);
      card.append(summary,detail);cards.push(card);
    }$('ranking').replaceChildren(...cards);
    $('date-values').replaceChildren(...IDS.map(id=>{const e=element('span');e.style.setProperty('--person','var(--'+id+')');e.append(element('span',t(id)),element('strong',money(point.values[id])));return e;}));
    $('total-note').textContent=LANG==='ko'?'남은 돈은 BIL(단기국채 ETF)에 투자합니다. 매매 설정의 비율은 처음 목돈 기준이며 배당은 재투자해요.':'Uninvested funds stay in BIL (Treasury bills). Trade-size percentages use initial cash; distributions are reinvested.';
    $('missing').textContent=RESULT.missingFear?(LANG==='ko'?`이 비교에 공포탐욕지수 관측이 없는 거래일 ${RESULT.missingFear}일이 있어 다니엘의 신호를 만들지 않았습니다.`:`Fear & Greed observations were absent for ${RESULT.missingFear} trading days; Daniel receives no invented signal.`):'';
    comparisonNote(point);log();marker();
  }
  function reason(trade){
    const k=trade.reason;
    if(k==='start')return LANG==='ko'?'첫날 목돈 전부 투자':'Invest all initial cash';
    if(k==='monthly')return LANG==='ko'?'매달 처음 목돈의 정해진 비율':'Monthly share of initial cash';
    if(k==='fear'||k==='greed')return (LANG==='ko'?'공포탐욕지수 ':'Fear & Greed ')+trade.fear+' · '+trade.signalDay+(LANG==='ko'?' 관측':' observation');
    const detail=LANG==='ko'?'공개 '+trade.filed+' · '+trade.period+' 분기':'Published '+trade.filed+' · Quarter '+trade.period;
    return (LANG==='ko'?({new:'신규 진입',add:'추가 매수',reduce:'보유 감소',exit:'전량 처분'}[k]||'공시 변화'):({new:'New holding',add:'Addition',reduce:'Reduction',exit:'Full disposal'}[k]||'Filing change'))+' · '+detail;
  }
  function legend(){
    $('legend').replaceChildren(...['',...IDS].map(id=>{
      const b=element('button',id?t(id)+' · '+SHORT[LANG][id]:(LANG==='ko'?'모두 보기':'Show everyone'));
      b.type='button';b.dataset.actor=id;b.setAttribute('aria-pressed',String(FOCUS===id));
      if(id)b.style.setProperty('--person','var(--'+id+')');
      b.addEventListener('click',()=>{stop();setFocus(id);});return b;
    }));
  }
  function setFocus(id){
    FOCUS=id;$('actor').value=id;
    for(const b of $('legend').querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.dataset.actor===id));
    LIMIT=6;log();draw();
  }
  function moments(){
    const final=RESULT.curve.at(-1),winner=M.rank(final,RESULT.options.amount)[0],low=P.drawdownMoment(RESULT,winner.id),first=P.firstTrade(RESULT,'daniel'),alicia=P.firstTrade(RESULT,'alicia');
    MOMENTS=[
      {id:'drop',actor:winner.id,index:low?.index,title:LANG==='ko'?'더 번 사람은 덜 떨어졌을까?':'Did earning more mean falling less?',
        body:LANG==='ko'?`${t(winner.id)} · 기간 수익률 ${pct(winner.return)} · 최대 하락 ${dropText(winner.drop)}`:`${t(winner.id)} · Period return ${pct(winner.return)} · Largest drop ${dropText(winner.drop)}`,
        note:low?(LANG==='ko'?`${t(winner.id)}의 총자산은 ${RESULT.curve[low.peakIndex].day}의 고점 ${money(low.peak)}에서 ${RESULT.curve[low.index].day} ${money(low.value)}까지 ${dropText(low.drop).replace('-','')} 하락했습니다.`:`${t(winner.id)} fell ${dropText(low.drop).replace('-','')} from a high of ${money(low.peak)} on ${RESULT.curve[low.peakIndex].day} to ${money(low.value)} on ${RESULT.curve[low.index].day}.`):(LANG==='ko'?'이 기간에 고점 대비 하락이 없었습니다.':'No decline from a previous high in this period.')},
      {id:'daniel',actor:'daniel',index:first?.index,title:LANG==='ko'?'공포를 기다린 다니엘, 언제 샀을까?':'When did Daniel finally buy?',
        body:first?(LANG==='ko'?`첫 매수 ${first.trade.day} · ${tradeMoney(first.trade.amount)}`:`First purchase ${first.trade.day} · ${tradeMoney(first.trade.amount)}`):(LANG==='ko'?'이 기간에는 주식 매수가 없었어요.':'No equity purchases in this period.'),
        note:first?(LANG==='ko'?`${first.trade.signalDay} 공포탐욕지수가 ${Number(first.trade.fear.toFixed(1))}인 것을 확인하고, 다음 거래일인 ${first.trade.day}에 ${tradeMoney(first.trade.amount)}만큼 투자했습니다.`:`After observing Fear & Greed at ${Number(first.trade.fear.toFixed(1))} on ${first.trade.signalDay}, Daniel invested ${tradeMoney(first.trade.amount)} on the next trading day, ${first.trade.day}.`):''},
      {id:'alicia',actor:'alicia',index:alicia?.index,title:LANG==='ko'?'공시를 따라간 알리시아의 첫 선택은?':'What was Alicia’s first disclosed pick?',
        body:alicia?`${alicia.trade.day} · ${alicia.trade.key} · ${tradeMoney(alicia.trade.amount)}`:(LANG==='ko'?'이 기간에는 주식 매수가 없었어요.':'No equity purchases in this period.'),
        note:alicia?(LANG==='ko'?`${alicia.trade.filed} 공개 공시를 확인한 뒤 ${alicia.trade.day} ${alicia.trade.key}에 ${tradeMoney(alicia.trade.amount)}만큼 투자했습니다. 버크셔 전체를 복제한 결과는 아닙니다.`:`After the ${alicia.trade.filed} disclosure, Alicia invested ${tradeMoney(alicia.trade.amount)} in ${alicia.trade.key} on ${alicia.trade.day}. This does not copy Berkshire’s entire portfolio.`):''}
    ];
    $('moments').replaceChildren(...MOMENTS.map(m=>{const b=element('button');b.type='button';b.dataset.moment=m.id;b.disabled=m.index==null;
      b.append(element('strong',m.title),element('span',m.body),element('span',b.disabled?(LANG==='ko'?'이동할 사건 없음':'No event to visit'):(LANG==='ko'?'그날 보기 →':'Visit this date →'),'moment-action'));
      b.addEventListener('click',()=>{stop();EVENT=m.id;setFocus(m.actor);seek(m.index);$('explorer').scrollIntoView({block:'start'});$('explorer-heading').focus({preventScroll:true});});return b;}));
  }
  function eventNote(){const m=MOMENTS.find(m=>m.id===EVENT&&m.index===INDEX);$('event-note').hidden=!m;$('event-note').textContent=m?.note||'';}
  function log(){
    const actor=$('actor').value,day=RESULT.curve[INDEX].day,rows=P.groupTrades(RESULT.trades,day,actor),opened=new Set([...$('log').querySelectorAll('details[open]')].map(e=>e.dataset.key));
    const list=rows.slice(0,LIMIT).map(group=>{const li=element('li'),detail=element('details');detail.dataset.key=group.key;detail.open=opened.has(group.key);const summary=element('summary'),time=element('time',group.day);time.dateTime=group.day;
      const description=LANG==='ko'?`${group.trades.length}건의 선택 · 매수 ${tradeMoney(group.buy)} / 매도 ${tradeMoney(group.sell)}`:`${group.trades.length} trades · Bought ${tradeMoney(group.buy)} / sold ${tradeMoney(group.sell)}`;
      summary.append(time,element('strong',t(group.actor)),element('span',description),element('span',LANG==='ko'?'자세히 ⌄':'Details ⌄','log-expand'));detail.append(summary);
      for(const r of group.trades){const ticker=['spx','ndx'].includes(r.key)?(r.key==='spx'?'SPY':'QQQ'):r.key;const line=element('div',undefined,'trade-line');line.append(element('strong',t(r.action==='buy'?'buyTrade':'sellTrade')+' · '+ticker),element('span',tradeMoney(r.amount)),element('p',reason(r)));detail.append(line);}li.append(detail);return li;});
    $('log').replaceChildren(...(list.length?list:[element('li',t('empty'))]));$('more').hidden=rows.length<=LIMIT;
  }
  const DASH=['7 4','','10 4','4 3','2 4'];
  function draw(){
    if(!RESULT||$('race').hidden)return;const svg=$('chart'),W=Math.max(200,Math.round(svg.clientWidth)),H=svg.clientHeight,L=W<500?45:62,R=W-12,T=15,B=H-30,rows=RESULT.curve;
    let lo=Infinity,hi=-Infinity;for(const r of rows)for(const v of Object.values(r.values)){lo=Math.min(lo,v);hi=Math.max(hi,v);}
    const pad=Math.max((hi-lo)*.1,RESULT.options.amount*.03);lo=Math.max(0,lo-pad);hi+=pad;
    const from=Date.parse(RESULT.from),span=Date.parse(RESULT.to)-from,x=d=>L+(Date.parse(d)-from)/span*(R-L),y=v=>B-(v-lo)/(hi-lo)*(B-T),n=v=>v.toFixed(2);GEOMETRY={W,H,L,R,T,B,x,y};
    let html=`<defs><clipPath id="elapsed"><rect id="elapsed-rect" x="${L}" y="0" width="${R-L}" height="${H}"/></clipPath></defs>`;
    for(let i=0;i<4;i++){const v=lo+(hi-lo)*i/3,yy=y(v);html+=`<path class="grid" d="M${L} ${n(yy)}H${R}"/><text x="${L-7}" y="${n(yy+4)}" text-anchor="end">${new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(v)}</text>`;}
    html+=`<path class="baseline" d="M${L} ${n(y(RESULT.options.amount))}H${R}"/>`;
    const ticks=W<500?3:5;for(let i=0;i<ticks;i++){const r=rows[Math.round(i*(rows.length-1)/(ticks-1))];html+=`<text x="${n(x(r.day))}" y="${H-7}" text-anchor="${i===0?'start':i===ticks-1?'end':'middle'}">${r.day.slice(0,7).replace('-','.')}</text>`;}
    IDS.forEach((id,j)=>{const path=rows.map((r,i)=>(i?'L':'M')+n(x(r.day))+' '+n(y(r.values[id]))).join(' '),alpha=!FOCUS||FOCUS===id?1:.16;html+=`<path class="curve future" style="--person:var(--${id});opacity:${alpha*.16}" stroke-dasharray="${DASH[j]}" d="${path}"/><path class="curve elapsed" clip-path="url(#elapsed)" style="--person:var(--${id});opacity:${alpha}" stroke-dasharray="${DASH[j]}" d="${path}"/>`;});
    html+=`<text x="${L+6}" y="${Math.max(T+12,y(RESULT.options.amount)-6)}" class="initial-label">${LANG==='ko'?'처음 목돈':'Initial cash'}</text>`;
    html+='<g id="replay-line"></g><g id="hover-line"></g>';svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('aria-label',t('chart'));svg.innerHTML=html;$('tooltip').hidden=true;marker();
  }
  function marker(){if(!RESULT||!GEOMETRY||!$('replay-line'))return;const g=GEOMETRY,p=RESULT.curve[INDEX],x=g.x(p.day);$('elapsed-rect').setAttribute('width',Math.max(0,x-g.L));$('replay-line').innerHTML=`<path class="replay-line" d="M${x} ${g.T}V${g.B}"/>`+IDS.filter(id=>!FOCUS||id===FOCUS).map(id=>`<circle cx="${x}" cy="${g.y(p.values[id])}" r="4" fill="var(--${id})"/>`).join('');}
  function hover(i){
    if(!RESULT||!GEOMETRY)return;HOVER=Math.max(0,Math.min(RESULT.curve.length-1,i));const p=RESULT.curve[HOVER],g=GEOMETRY,x=g.x(p.day);
    $('hover-line').innerHTML=`<path class="crosshair" d="M${x} ${g.T}V${g.B}"/>`+IDS.map(id=>`<circle cx="${x}" cy="${g.y(p.values[id])}" r="3" fill="var(--${id})"/>`).join('');
    const tip=$('tooltip');tip.replaceChildren(element('b',p.day+(HOVER!==INDEX?(LANG==='ko'?' · 미리보기':' · preview'):'')),...IDS.map(id=>{const row=element('div');row.append(element('span',t(id)),element('span',money(p.values[id])));return row;}),element('p',LANG==='ko'?'누르면 모든 결과가 이 날짜로 바뀝니다.':'Select to update all results to this date.'));tip.hidden=false;tip.style.top='6px';tip.style.left=Math.max(4,Math.min(g.W-tip.offsetWidth-4,x+12))+'px';
  }
  function pointer(e){if(!RESULT||!GEOMETRY)return;const g=GEOMETRY,rect=$('chart').getBoundingClientRect(),fraction=Math.max(0,Math.min(1,(e.clientX-rect.left-g.L)/(g.R-g.L))),time=Date.parse(RESULT.from)+fraction*(Date.parse(RESULT.to)-Date.parse(RESULT.from));
    let best=0,distance=Infinity;RESULT.curve.forEach((r,i)=>{const d=Math.abs(Date.parse(r.day)-time);if(d<distance){distance=d;best=i;}});hover(best);}
  function stop(){if(TIMER)clearInterval(TIMER);TIMER=null;$('play').textContent=t('play');}
  function seek(i){if(!RESULT)return;INDEX=Math.max(0,Math.min(RESULT.curve.length-1,i));HOVER=INDEX;LIMIT=6;hideTip();render();eventNote();}
  $('settings').addEventListener('submit',e=>{e.preventDefault();compare();if(RESULT){$('condition-panel').open=false;$('condition-panel').querySelector('summary').focus();}});
  $('settings').addEventListener('input',()=>{stop();$('pending').hidden=!RESULT;});
  $('timeline').addEventListener('input',()=>{stop();seek(Number($('timeline').value));});
  $('first').addEventListener('click',()=>{stop();seek(0);});$('last').addEventListener('click',()=>{stop();seek(RESULT.curve.length-1);});
  $('play').addEventListener('click',()=>{if(!RESULT)return;if(TIMER){stop();return;}if(INDEX===RESULT.curve.length-1)seek(0);$('play').textContent=t('pause');TIMER=setInterval(()=>{seek(INDEX+Math.max(1,Math.ceil(RESULT.curve.length/140)));if(INDEX===RESULT.curve.length-1)stop();},180);});
  $('actor').addEventListener('change',()=>{stop();setFocus($('actor').value);});$('more').addEventListener('click',()=>{LIMIT+=6;log();});
  $('chart').addEventListener('pointermove',e=>{if(e.pointerType==='mouse')pointer(e);});$('chart').addEventListener('click',e=>{if(!RESULT)return;stop();pointer(e);seek(HOVER);});
  function hideTip(){$('tooltip').hidden=true;if($('hover-line'))$('hover-line').innerHTML='';}
  $('chart').addEventListener('pointerleave',hideTip);$('chart').addEventListener('blur',hideTip);
  $('chart').addEventListener('keydown',e=>{if(!RESULT)return;if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();stop();seek(e.key==='Home'?0:e.key==='End'?RESULT.curve.length-1:INDEX+(e.key==='ArrowLeft'?-1:1));}else if(e.key==='Escape')hideTip();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  if(typeof ResizeObserver==='function')new ResizeObserver(draw).observe($('chart'));else window.addEventListener('resize',draw);
  language();
  fetch('/data/olympics/race.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json();}).then(raw=>{
    DATA=M.prepare(raw);for(const id of ['start','end']){$(id).min=raw.from;$(id).max=raw.to;$(id).value=raw[id==='start'?'from':'to'];}
    $('apply').disabled=false;range();compare();
  }).catch(()=>{ERROR='error';$('status').textContent=t(ERROR);$('status').hidden=false;$('race').hidden=true;$('apply').disabled=true;});
})();
