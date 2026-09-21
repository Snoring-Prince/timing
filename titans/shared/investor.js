window.MARKS = { url: "https://api.elbstream.com/logos/{idType}/{id}?format=png&size=64" };

/* 설정 블록의 짧은 이름. 사전과 화면이 둘 다 이것만 읽습니다 —
   투자자를 바꿀 때 고칠 곳이 `window.TITAN` 하나로 끝나는 이유입니다.
   블록이 없어도 화면이 안 죽게 기본값을 둡니다. */
const TT = Object.assign(
  { slug:"", cik:"", data:"", name:{en:"this investor", ko:"이 투자자"},
    since:"", prices:"" },
  window.TITAN||{});
/* 지금 언어로 된 이름. `applyLang()` 이 언어를 바꾸면 따라 바뀝니다. */
const tName=()=>TT.name[LANG]||TT.name.en;
const esc=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");

const D={
en:{
  locale:"en-US", dir:"ltr", tab:"English",
  docTitle:(n,y)=>`${n} portfolio — every 13F filing since ${y}`,
  metaDesc:n=>`${n} holdings in its latest SEC 13F filing — position sizes, share changes and estimated returns based on quarter-end snapshots.`,
  brand:"Titans' picks",
  tagline:n=>`${n} holdings · latest filing`,
  mobileGuide:"Numbers, left to right: shares held · share change this quarter · estimated return. Right: value · portfolio weight.",
  tradeBasis:"Trade amounts are estimates from share changes and quarter-end prices. Full exits use the previous quarter-end value.",
  asOf:d=>`As of ${d}`,
  filedOn:d=>`filed ${d}`,
  quarterHead:"This quarter",
  kNew:"new", kAdd:"added", kTrim:"trimmed", kHold:"held", kOut:"exited",
  positions:n=>`${n} positions`,
  bought:(n,v)=>`<i>Largest buy</i><span>${n}</span><em>${v} est.</em>`,
  sold:(n,v)=>`<i>Largest sale</i><span>${n}</span><em>${v} est.</em>`,
  evNew:"New", evBack:"Back in", evOut:"Sold out",
  heldFor:"held",
  costArrow:d=>`return = estimated average cost \u2192 price on ${d} · before dividends`,
  /* 가운데 칸은 좁다. **왜 숫자가 없는지만** 짧게 적고, 긴 설명은 각주가 한다.
     `집계 전` 은 우리 자료(1998년 첫 공시)보다 먼저 들고 있던 종목이다 —
     연도를 줄마다 적어 봐야 방문자는 그 해가 무슨 뜻인지 모른다(사용자 지적). */
  noRetOld:"pre-records", noRetNew:"just in",
  yr:n=>n<1?`${Math.round(n*12)} mo`:(n%1?`${n.toFixed(1)} yr`:`${n} yr`),
  /* 목록 머리글. **안 변하는 말은 머리에 한 번만** 적는다(4번 성적표와 같은 판단). */
  colShares:"Shares held", colQtr:"This quarter", colRet:"Est. return", colVal:"Value · weight",
  lifeSum:(n,lo,hi)=>`${n} quarters · low ${lo} → high ${hi}`,
  lifeThin:"only one filing — nothing to draw yet",
  lifeSpans:["1Y","5Y","10Y","15Y"],
  lifeSpanLab:"how far back to show",
  lifePrior:(b,s)=>`<span>Earlier</span><span>BUY <em class="up">${b}</em></span><span>SELL <em class="down">${s}</em></span>`,
  close:"Close",
  impliedPrice:"Implied quarter-end price",
  priceNote:(d)=>`Price lines show daily closing prices through ${fdate(d)}, adjusted for stock splits, without dividend adjustments. For grouped share classes, the tooltip identifies the class shown by its ticker. Trade bars show net changes between filings, not daily trading volume; no trades after the latest filing are inferred.`,
  lifeQuiet:"never bought or sold across this history",
  lifeScroll:"drag sideways for earlier years",
  buy:"BUY", sell:"SELL",
  same:"held",
  topOnly:(n,p)=>`Top ${n} shown — ${p} of the portfolio`,
  allShown:n=>`All ${n} positions shown`,
  foldOpen:n=>"Show more",
  prevTick:"tick marks last quarter's share",
  noData:"Could not load the filings.",
  aboutH:"How to read this",
  footTitle:"Source and limits",
  /* 각주는 **함수**입니다 — 첫 공시 연도·분할 목록·집계 전 종목이 자료에서
     오므로, 분기가 새로 나와 그것들이 바뀌면 글도 같이 바뀝니다. */
  foot:(firstY,splits,pre)=>[
    `Source: SEC Form 13F-HR, filed by ${TT.name.en} (CIK ${TT.cik}). US government work \u2014 public domain.`,
    "A 13F is filed 45 days after the quarter ends, so these holdings are at least six weeks old and may already have changed.",
    "A 13F shows US-listed long equity positions only. Bonds, cash, foreign listings, wholly owned businesses and short positions are not in it.",
    "Values are what the filing states for the quarter-end date. Dividing value by share count gives an implied quarter-end price — not a trade price.",
    "A 13F is a quarter-end snapshot, so when inside the quarter a trade happened is not knowable. The chart\u2019s trade bars therefore span the whole stretch from the previous filing to that one \u2014 they mean \u201Csomewhere in here\u201D, not a single day.",
    "Share classes of one issuer are shown on one line (marked A+C and so on) because one decision usually moves both. Preferred stock is kept on its own line.",
    `“pre-records” marks a holding that was already in the first filing we have (${firstY||"1998"}), so the buying is not visible and no cost or return can be worked out for it.${pre&&pre.length?` Right now that is ${pre.join(", ")}.`:""}`,
    "Average cost is an estimate. Each quarter's share change is priced at the midpoint of that quarter's and the previous quarter's implied price, then carried forward on an average-cost basis. Actual trades happened at prices we cannot see, so the estimate can be off by a wide margin.",
    `Stock splits are detected from the filings themselves — a whole-number jump in share count matched by the same drop in implied price.${splits&&splits.length?` Among the holdings shown: ${splits.join(", ")}.`:""}`,
    "The return shown is price only. Dividends received over the years are not in it, so the real outcome was better than the number.",
    "Sector labels come from the SIC industry code the SEC assigns each company. One code per company, so a holding that spans several businesses is filed under one of them.",
    "Company marks are from simple-icons (CC0-1.0) and are stored in this repository, not loaded from anywhere else. The shapes are public domain; the trademarks belong to their owners and are used here only to identify a holding. Companies that set does not cover are shown as initials instead.",
    "This page reports what was filed. It is not advice, and nothing here is a recommendation to buy or sell."
  ]
},
ko:{
  locale:"ko-KR", dir:"ltr", tab:"한국어",
  docTitle:(n,y)=>`${n} 포트폴리오 — ${y}년부터의 13F 공시`,
  metaDesc:n=>`${n}의 최근 SEC 13F 공시 기준 보유 종목 — 분기말 기록으로 비중, 주식수 증감과 추정 수익률을 살펴봅니다.`,
  brand:"대가들의 선택",
  tagline:n=>`${n} · 최근 공시 기준 보유 종목`,
  mobileGuide:"숫자는 왼쪽부터 보유 주식수 · 이번 분기 주식수 증감 · 추정 수익률입니다. 오른쪽은 금액 · 전체 보유 금액에서의 비중입니다.",
  tradeBasis:"매매 금액은 주식수 증감과 분기말 가격으로 추정합니다. 전량 매도는 직전 분기말 보유 금액을 사용합니다.",
  asOf:d=>`${d} 기준`,
  filedOn:d=>`${d} 공시`,
  quarterHead:"이번 분기",
  kNew:"신규", kAdd:"확대", kTrim:"축소", kHold:"유지", kOut:"전량매도",
  positions:n=>`${n}종목`,
  /* **줄글이 아니라 이름표 + 값입니다** (사용자 요청). 한 화면에 나란히 놓이는
     두 줄이라 같은 꼴이어야 견줘집니다 — "가장 많이 산 것은 … 입니다" 는
     라벨이 숫자보다 자리를 더 차지하던 성적표와 같은 문제였습니다. */
  bought:(n,v)=>`<i>최대 매수</i><span>${n}</span><em>${v} 추정</em>`,
  sold:(n,v)=>`<i>최대 매도</i><span>${n}</span><em>${v} 추정</em>`,
  evNew:"신규", evBack:"재진입", evOut:"전량매도",
  heldFor:"보유",
  costArrow:d=>`수익률 = 추정 매수 평균가 \u2192 ${d} 가격 · 배당 제외`,
  /* 가운데 칸은 좁다. **왜 숫자가 없는지만** 짧게 적고, 긴 설명은 각주가 한다.
     `1998년 이전` 이라고 적었더니 사용자가 "의미를 잘 모르겠다"고 했다 —
     방문자는 1998년이 우리 자료의 시작이라는 걸 알 길이 없다. */
  noRetOld:"집계 전", noRetNew:"이번 분기",
  yr:n=>n<1?`${Math.round(n*12)}개월`:(n%1?`${n.toFixed(1)}년`:`${n}년`),
  /* 목록 머리글. **안 변하는 말은 머리에 한 번만** 적는다(4번 성적표와 같은 판단). */
  colShares:"보유 주식 수", colQtr:"이번 분기", colRet:"추정 수익률", colVal:"금액 · 비중",
  lifeSum:(n,lo,hi)=>`${n}분기 · 최저 ${lo} → 최고 ${hi}`,
  lifeThin:"공시가 한 번뿐이라 아직 그릴 것이 없습니다",
  lifeSpans:["1년","5년","10년","15년"],
  lifeSpanLab:"얼마나 거슬러 볼까",
  lifePrior:(b,s)=>`<span>이 기간 이전</span><span>매수 <em class="up">${b}</em>건</span><span>매도 <em class="down">${s}</em>건</span>`,
  close:"종가",
  impliedPrice:"공시 기준 분기말 가격",
  priceNote:(d)=>`주가선은 ${fdate(d)}까지의 일별 종가이며, 액면분할만 보정하고 배당은 반영하지 않습니다. 여러 종류를 합친 종목은 말풍선의 티커에 해당하는 종류의 가격을 표시합니다. 막대는 공시 사이의 보유 주식수 순변화이며 일별 거래량이 아닙니다. 마지막 공시 이후의 매매는 추정하지 않습니다.`,
  lifeQuiet:"이 기간에 사고판 적이 없습니다",
  lifeScroll:"옆으로 끌면 그 이전이 나옵니다",
  buy:"BUY", sell:"SELL",
  same:"유지",
  topOnly:(n,p)=>`상위 ${n}종목만 · 전체의 ${p}`,
  allShown:n=>`${n}종목 전부 펼침`,
  foldOpen:n=>"더 보기",
  prevTick:"눈금은 직전 분기 비중",
  noData:"공시를 불러오지 못했습니다.",
  aboutH:"보는 법",
  footTitle:"출처와 한계",
  foot:(firstY,splits,pre)=>[
    `출처: ${TT.name.ko}(CIK ${TT.cik})가 SEC 에 낸 Form 13F-HR. 미국 정부 저작물이라 퍼블릭 도메인입니다.`,
    "13F 는 분기가 끝나고 45일 뒤에 냅니다. 그래서 여기 보이는 것은 최소 6주 전의 상태이고, 그 사이에 이미 바뀌었을 수 있습니다.",
    "13F 에는 미국 상장 주식의 매수 포지션만 나옵니다. 채권·현금·해외 상장·통째로 소유한 회사·공매도는 들어 있지 않습니다.",
    "금액은 공시에 적힌 분기말 값입니다. 금액을 주식수로 나누면 분기말 가격이 나오는데, 실제 체결가가 아닙니다.",
    "13F 는 분기말 스냅샷뿐이라 그 분기 안에서 언제 사고팔았는지는 알 수 없습니다. 그래서 차트의 매매 막대는 한 점이 아니라 직전 공시부터 그 공시까지를 통째로 덮습니다 — ‘이 사이 어딘가’ 라는 뜻입니다.",
    "같은 회사의 여러 종류 주식은 한 줄로 묶었습니다(A+C 처럼 표시). 한 번의 결정이 대개 둘을 같이 움직이기 때문입니다. 우선주는 성격이 다르므로 따로 둡니다.",
    `‘집계 전’ 은 우리가 가진 첫 공시(${firstY||"1998"}년)에 이미 들어 있던 종목입니다. 사들이는 장면이 안 보이므로 매수가도 수익률도 낼 수 없습니다.${pre&&pre.length?` 지금은 ${pre.join(" · ")} 가 여기 해당합니다.`:""}`,
    "매수 평균가는 추정치입니다. 분기마다 늘어난 주식수를 그 분기와 직전 분기 가격의 중간값으로 사들인 것으로 보고, 이동평균 방식으로 이어 계산했습니다. 실제 체결가는 공시에 없으므로 추정이 크게 빗나갈 수 있습니다.",
    `액면분할은 공시 자체에서 찾아냅니다 — 주식수가 정수 배수로 뛰면서 가격이 꼭 그만큼 내려간 분기입니다.${splits&&splits.length?` 지금 보이는 종목 중에는 ${splits.join(", ")} 가 있습니다.`:""}`,
    "수익률에는 배당이 들어 있지 않습니다. 여러 해 받은 배당만큼 실제 결과는 여기 적힌 숫자보다 낫습니다.",
    "섹터는 SEC 가 회사마다 매기는 업종 코드(SIC)를 옮긴 것입니다. 회사당 하나뿐이라, 여러 사업을 하는 회사도 그중 하나로 적힙니다.",
    "회사 마크는 simple-icons(CC0-1.0)에서 가져와 이 저장소에 넣어 둔 것입니다. 바깥에서 불러오지 않습니다. 도형은 퍼블릭 도메인이고 상표는 각 회사 것이며, 여기서는 어느 회사를 들고 있는지 가리키는 용도로만 씁니다. 그 세트에 없는 회사는 이름 첫 글자로 대신합니다.",
    "이 화면은 공시된 내용을 그대로 옮길 뿐입니다. 투자 자문이 아니고, 무엇을 사거나 팔라는 뜻도 아닙니다."
  ]
}
};

/* 상승을 빨강으로 읽는 문화권 — 본 사이트와 같은 집합·같은 팔레트 */
const REDUP=new Set(["ko","ja","zh"]);
const PAL={
  redUp  :{up:"#C4362C",down:"#1F5FA9",upRGB:"196,54,44", downRGB:"31,95,169"},
  greenUp:{up:"#1B7F4B",down:"#C4362C",upRGB:"27,127,75", downRGB:"196,54,44"}
};

let LANG="en", L10N=D.en, LOCALE="en-US";

function pickLang(){
  const two=s=>String(s||"").slice(0,2).toLowerCase();
  try{ const q=two(new URLSearchParams(location.search).get("lang")); if(q&&D[q])return q; }catch(e){}
  try{ const s=localStorage.getItem("dt.lang"); if(s&&D[s])return s; }catch(e){}
  const navs=(navigator.languages&&navigator.languages.length)?navigator.languages:[navigator.language||"en"];
  for(const l of navs){ const k=two(l); if(D[k])return k; }
  return "en";
}
function pickLocale(lang){
  const navs=(navigator.languages&&navigator.languages.length)?navigator.languages:[navigator.language||""];
  for(const l of navs) if(String(l).slice(0,2).toLowerCase()===lang) return l;
  return D[lang].locale;
}
const tx=(k,...a)=>{ const v=(k in L10N)?L10N[k]:D.en[k]; return typeof v==="function"?v(...a):v; };

/* Every investor mounts this same shell; its page keeps only static SEO fallback. */
function mountInvestorShell(){
  document.body.innerHTML=`<div class="wrap">

  <header class="masthead">
    <div>
      <!-- 브랜드는 눈썹줄로. 번역하지 않는 이름이 아니라 두 언어가 다르므로
           applyLang() 이 채운다(본 사이트의 eyebrow 와 다른 점). -->
      <p class="eyebrow" id="brand">Titans' picks</p>
      <!-- render() 가 taglineHTML() 로 갈아끼운다. 투자자 이름만 진한 잉크로
           떼어 놓고 앞에 이름표를 단다 — 어느 투자자의 화면인지가 제목에서
           바로 읽혀야 한다. -->
      <h1 id="tagline">This investor holdings · latest filing</h1>
    </div>
    <div class="mast-right">
      <div class="seg" id="langtabs" role="group" aria-label="Language"></div>
      <div class="stamp" id="stamp"></div>
    </div>
  </header>
  <section class="panel fade" id="quarter" hidden>
    <h2 id="qhead">This quarter</h2>
    <div class="tally" id="tally"></div>
    <div class="says" id="says"></div>
    <p class="trade-basis" id="tradebasis"></p>
    <div class="events" id="events" hidden></div>
  </section>

  <section class="panel fade" id="book" hidden>
    <h2 id="bookhead"></h2>
    <p class="cap" id="bookcut"></p>
    <p class="cap" id="bookcap"></p>
    <p class="mobile-guide" id="mobileguide"></p>
    <div class="rowin head" id="colhead">
      <div class="who"><b class="caret"></b></div>
      <div class="mid">
        <span class="hold" id="c1"></span>
        <span class="act" id="c2"></span>
        <span class="ret" id="c3"></span>
      </div>
      <div class="amt"><span id="c4"></span></div>
    </div>
    <ul class="rows" id="top"></ul>
    <details class="fold" id="fold" hidden>
      <summary><span id="foldttl"></span></summary>
      <ul class="rows" id="rest"></ul>
    </details>
    <p class="legend"><i></i><span id="legend"></span></p>
  </section>

  <footer class="foot">
    <h2 id="foothead">Source and limits</h2>
    <div id="footbody"></div>
    <a class="back" href="/">← itpaidoff.com</a>
  </footer>

</div>`;
}
if(document.body)mountInvestorShell();

/* ══ 데이터 ═══════════════════════════════════════════════════════════
   화면은 자기 집 파일만 읽습니다. Actions 가 주 1회 SEC 에서 받아
   window.TITAN.data가 가리키는 파일에 저장합니다(scripts/fetch_13f.py).
══════════════════════════════════════════════════════════════════════ */
let RAW=null, LOADED=false, FIRSTY="";

/* 같은 발행사의 여러 종류 주식을 한 줄로 묶는다.
   CUSIP 아홉 자리 중 **앞 여섯 자리가 발행사**다. 알파벳 A(02079K305)와
   C(02079K107)가 그래서 같은 묶음이 된다.
   **우선주는 묶지 않는다** — 표만 없는 보통주(알파벳 C)와 달리 배당·청산
   순위가 다른 별개의 증권이다. 28년치에 딱 하나 있다(Sealed Air PFD CVA). */
const ISPFD=/\bPFD\b|PREFERRED/;
const gkey=h=>h.cusip.slice(0,6)+(ISPFD.test((h.class||"").toUpperCase())?"|P":"");

function merge(q){
  const g=new Map();
  for(const h of q.holdings){
    const k=gkey(h);
    let a=g.get(k);
    if(!a){ a={key:k,name:h.name,value:0,shares:0,classes:[],n:0,cusip:h.cusip,top:0}; g.set(k,a); }
    a.value+=h.value; a.shares+=h.shares; a.n++;
    /* 대표 CUSIP 은 그 묶음에서 제일 큰 줄의 것. ISIN 을 만들려면 여섯 자리로는
       부족하고 아홉 자리가 다 있어야 한다. */
    if(h.value>a.top){ a.top=h.value; a.cusip=h.cusip; }
    a.classes.push(h.class||"");
    a.name=h.name;
  }
  return g;
}
/* 묶음에 붙일 꼬리표. 두 줄 이상일 때만 A+C 처럼 적는다 — 합쳤다는 사실을
   화면에 밝히지 않으면 공시와 대조하는 사람이 줄 수를 못 맞춘다. */
function classTag(a){
  if(a.n<2) return "";
  const s=[...new Set(a.classes.map(c=>{
    const m=String(c).toUpperCase().match(/(?:CL|CLASS|SER|SERIES)\s*([A-Z])\b/);
    return m?m[1]:null;
  }).filter(Boolean))].sort();
  return s.length>1?s.join("+"):"";
}

const num=n=>Number(n||0).toLocaleString(LOCALE);
const pct=n=>`${n.toFixed(1)}%`;
const weightPct=n=>n>0&&n<0.1?"<0.1%":pct(n);
function money(v){
  const b=v/1e9;
  if(b>=100) return `$${b.toFixed(0)}B`;
  if(b>=1)   return `$${b.toFixed(1)}B`;
  const m=v/1e6;
  return m>=1?`$${m.toFixed(0)}M`:`$${(v/1e3).toFixed(0)}K`;
}
/* **영어에서 `shares` 를 떼었습니다** (2026-09-17). 열 머리글이 이미
   `SHARES HELD`·`THIS QUARTER` 라고 적고 있어서 26줄에 같은 말이 52번
   되풀이됐고, 글자를 14px 로 올리자 그 폭 때문에 **영어 섹터가 둘째 줄로
   밀려났습니다**(`Financial Services` 가 이름 아래로 떨어짐). 4번의
   "라벨이 숫자보다 자리를 더 차지했습니다 … 열 머리에 한 번만" 과 같은 자리입니다.

   한국어의 `주` 는 뗄 수 없습니다 — `2.28억` 만 남기면 무엇이 2.28억인지
   알 수 없습니다. 원래도 짧아서 밀어낼 일이 없습니다. */
function shortShares(n){
  if(LANG==="ko"){
    if(n>=1e8) return `${(n/1e8).toFixed(n>=1e9?0:2)}억주`;
    if(n>=1e4) return `${Math.round(n/1e4).toLocaleString(LOCALE)}만주`;
    return `${num(n)}주`;
  }
  if(n>=1e9) return `${(n/1e9).toFixed(2)}B`;
  if(n>=1e6) return `${(n/1e6).toFixed(1)}M`;
  return num(n);
}
function fdate(iso){
  if(LANG==="ko") return String(iso).replace(/-/g,".");
  try{ return new Intl.DateTimeFormat(LOCALE,{year:"numeric",month:"short",day:"numeric"})
        .format(new Date(iso+"T00:00:00Z")); }
  catch(e){ return String(iso); }
}
/* 종목 이름은 공시에 전부 대문자로 적혀 있다(APPLE INC). 그대로 두면
   화면이 소리지르는 것처럼 보이므로 낱말머리만 대문자로 내린다.
   두 글자 이하 낱말과 이미 섞여 있는 이름은 그대로 둔다. */
/* 진짜 약어만 대문자로 남긴다. Inc·Corp·Co 까지 대문자로 두면 "Apple INC" 가 된다. */
const KEEP=new Set(["IBM","HP","NVR","USA","US","UK","AT&T","PLC","LLC","NV","SA","AG","ADR","REIT","MTN"]);
const SMALL=new Set(["of","and","the","for","de","la"]);
function title(s){
  if(/[a-z]/.test(s)) return s;
  return s.split(/\s+/).map((w,i)=>{
    if(KEEP.has(w.replace(/[^A-Z&.]/g,""))) return w;
    const low=w.toLowerCase();
    return (i>0&&SMALL.has(low))?low:w.charAt(0)+low.slice(1);
  }).join(" ");
}

/* ══ 그리기 ══════════════════════════════════════════════════════════ */
function build(){
  const qs=RAW.quarters;
  const cur=qs[qs.length-1], prv=qs[qs.length-2];
  const C=merge(cur), P=prv?merge(prv):new Map();
  const tc=[...C.values()].reduce((s,a)=>s+a.value,0);
  const tp=[...P.values()].reduce((s,a)=>s+a.value,0);

  /* 연속 보유 시작 분기. 끊겼다가 다시 들어온 것은 다시 들어온 시점부터 센다 —
     "10년 보유"가 중간에 판 3년을 포함하면 거짓말이 된다. */
  const seen=qs.map(q=>new Set(q.holdings.map(gkey)));
  const startOf=k=>{
    let i=qs.length-1;
    while(i>0 && seen[i-1].has(k)) i--;
    return {period:qs[i].period, qtrs:qs.length-i};
  };
  const everBefore=k=>seen.slice(0,-1).some(s=>s.has(k));

  /* 평균단가는 첫 분기부터 되짚어야 나온다 — 111개 분기를 한 번만 묶어 둔다 */
  const snaps=qs.map(merge);
  QS=qs.map(q=>String(q.period));      // lifeOf 가 분기 이름을 붙일 때 씁니다
  SPLITS=[];                           // 각주용. lifeOf 가 아래 map 에서 채웁니다

  const list=[...C.values()].map(a=>{
    const p=P.get(a.key);
    const st=startOf(a.key);
    /* 현재 분기도 차트와 같은 분할 보정을 합니다. 분할로 늘어난 주식은
       매수가 아닙니다 — 증감·계기판·최대 매수 모두 같은 기준이어야 합니다. */
    const f=p&&p.shares>0&&p.value>0&&a.shares>0&&a.value>0
      ?splitFactor(a.shares/p.shares,(p.value/p.shares)/(a.value/a.shares)):null;
    const prevShares=p?p.shares*(f||1):null;
    const dn=p?a.shares-prevShares:a.shares;
    const dsh=(prevShares>0)?(a.shares/prevShares-1):null;
    const cb=costBasis(snaps,a.key);
    return {
      ...a,
      w:a.value/tc*100,
      wPrev:p?p.value/tp*100:null,
      dsh,
      flat:dsh!==null&&Math.abs(dsh)<5e-4,
      isNew:!p,
      back:!p&&everBefore(a.key),
      start:st.period, years:st.qtrs/4,
      avgCost:cb.avg, nowPrice:cb.last,
      /* 첫 공시(1998-12-31)에 이미 들어 있던 종목은 사들이는 장면이 안 보인다.
         그 값을 평균단가라고 적으면 "1998년에 그 값에 샀다"는 거짓말이 된다. */
      preData:cb.first===0,
      freshIn:st.qtrs<=1,
      /* 이번 분기에 사고판 몫을 분기말 가격으로 환산한다. 비중 변화는 가격이
         섞여 있어 행동을 말해 주지 않는다 — 주식수 차이만 쓴다. */
      /* 가운데 칸에 '몇 주 늘었나'를 적으려면 비율이 아니라 **주식수 차이**가
         필요하다. 비율(dsh)은 판정에, 이 값(dn)은 화면 표기에 쓴다. */
      dn,
      /* 펼쳤을 때 그릴 분기 시계열. 저장소 파일 하나로 만들어지므로 주 1회
         워크플로가 13F 를 갱신하면 차트도 저절로 따라옵니다. */
      life:lifeOf(snaps,a.key),
      netUSD:dn*(a.shares>0?a.value/a.shares:0)
    };
  }).sort((x,y)=>y.value-x.value);

  /* 이번 분기에 통째로 사라진 묶음 */
  const out=prv?[...P.values()].filter(a=>!C.has(a.key)).map(a=>{
    let i=qs.length-2; const k=a.key;
    while(i>0 && seen[i-1].has(k)) i--;
    return {...a, years:(qs.length-1-i)/4, netUSD:-a.value};
  }).sort((x,y)=>y.value-x.value):[];

  /* 각주에 들어갈 두 목록. **둘 다 자료에서 뽑습니다** — 손으로 적어 두면
     분할이 한 번 더 일어나거나 코카콜라를 파는 날 조용히 거짓말이 됩니다
     (CLAUDE.md 9-3 의 "사람이 붙어야 하는 표는 결국 낡습니다"). */
  const splits=[];
  for(const r of list) for(const sp of SPLITS)
    if(sp.key===r.key) splits.push(`${title(r.name)} ${sp.f}:1(${String(sp.q).slice(0,4)})`);
  const preNames=list.filter(r=>r.preData).map(r=>title(r.name));

  return {cur,prv,list,out,tc,tp,splits,preNames};
}

function tallyOf(B){
  let nw=0,add=0,trim=0,hold=0;
  for(const r of B.list){
    if(r.isNew) nw++;
    else if(r.flat) hold++;
    else if(r.dsh>0) add++;
    else if(r.dsh<0) trim++;
    else hold++;
  }
  return {nw,add,trim,hold,out:B.out.length};
}

/* 해석 문장 — **행동만 적습니다.** 속마음("좋게 본다")도, 앞일("지금이 기회")도
   쓰지 않습니다. 13F 에는 "왜"가 없고 무엇을·얼마나만 있습니다. */
function says(B,T){
  const p=[];
  const buys=B.list.filter(r=>r.netUSD>0).sort((a,b)=>b.netUSD-a.netUSD);
  /* 전량 매도는 이번 분기 가격이 없으므로 직전 분기말 보유 금액으로 비교합니다.
     실제 매도 대금이 아닙니다 — 화면의 계산 안내에서 기준 차이를 밝힙니다. */
  const sells=[...B.list.filter(r=>r.netUSD<0),...B.out].sort((a,b)=>a.netUSD-b.netUSD);
  if(buys[0]) p.push(tx("bought",title(buys[0].name),money(buys[0].netUSD)));
  if(sells[0]) p.push(tx("sold",title(sells[0].name),money(-sells[0].netUSD)));
  /* **"한 주도 안 움직인 종목 수" 줄은 뺐습니다** (사용자 요청) — 바로 위
     다섯 칸 계기판의 `유지` 가 이미 같은 숫자를 적고 있습니다. */
  return p;
}

/* ══ 회사 마크 ═══════════════════════════════════════════════════════
   CUSIP 앞 여섯 자리(발행사)로 찾습니다. 화면이 묶는 단위와 같아서
   알파벳 A 와 C 가 한 마크를 씁니다.

   **저장소에 박아 둡니다. 바깥에서 받아오지 않습니다.** 로고를 남의 서버에서
   불러오면 그쪽이 문을 닫는 날 화면이 조용히 빈칸이 됩니다 — 이 프로젝트가
   이미 두 번 겪은 일입니다(CLAUDE.md 11번). 실제로 무료로 쓰던 Clearbit
   로고 API 가 2025년 말에 닫혔습니다. 방문자 IP 가 새는 것도 막힙니다.

   출처: simple-icons (CC0-1.0). 도형 자체는 퍼블릭 도메인이고, 상표는 각
   회사 것입니다 — 여기서는 "무엇을 들고 있나"를 가리키는 용도로만 씁니다.

   **없는 회사가 더 많습니다.** 개발자용 브랜드 세트라 보험·에너지·산업재는
   거의 안 들어 있습니다(상위 10종목 중 다섯: 셰브런·옥시덴탈·처브·무디스·
   크래프트하인즈). 없으면 이름 첫 글자 타일로 대신합니다 — 빈칸을 두면
   그림을 못 불러온 것처럼 보입니다.

   추가하려면 한 줄 더 넣으면 됩니다: "CUSIP6":{h:"색", t:"이름", d:"path"}
══════════════════════════════════════════════════════════════════ */
/* ── ISIN 은 CUSIP 에서 만듭니다 ──────────────────────────────────
   미국 종목의 ISIN = "US" + CUSIP 아홉 자리 + 체크숫자 한 자리.
   체크숫자는 글자를 A=10 … Z=35 로 편 뒤 Luhn 으로 냅니다.
   문서 예시와 대조해 확인했습니다 — 594918104 → US5949181045,
   166764100 → US1667641005(문서의 뉴스 응답에 Chevron Corp. 으로 나옵니다).

   **첫 글자가 숫자가 아니면 미국 발행사가 아닙니다**(CINS). 처브가 그렇습니다
   (H1467J104 — 스위스). 그런 종목은 ISIN 을 지어낼 수 없으니 티커로 찾습니다. */
function isinCheck(body){
  let s="";
  for(const c of body.toUpperCase())
    s += /[0-9]/.test(c) ? c : String(c.charCodeAt(0)-55);
  let sum=0;
  for(let i=s.length-1;i>=0;i--){
    let d=+s[i];
    if((s.length-1-i)%2===0){ d*=2; if(d>9) d-=9; }
    sum+=d;
  }
  return (10-(sum%10))%10;
}
function usISIN(cusip){
  const c=String(cusip||"").toUpperCase();
  if(c.length!==9||!/^[0-9]/.test(c)) return null;   // CINS = 미국 발행사가 아님
  return "US"+c+isinCheck("US"+c);
}
/* ISIN 을 못 만드는 종목의 티커. **손으로 적지 않습니다.**
   `scripts/fetch_tickers.py` 가 주 1회 OpenFIGI 에서 받아
   `data/titans/tickers.json` 에 저장한 것을 그대로 읽습니다.
   못 받았거나 파일이 없으면 비어 있고, 마크는 글자 타일로 떨어집니다. */
let QS=[];
/* 각주에 적는 액면분할 목록입니다. **손으로 적어 두면 다음 분할 때 낡습니다** —
   코드가 이미 찾아내고 있으므로 찾은 것을 그대로 적습니다(`lifeOf` 가 채웁니다). */
let SPLITS=[];
/* 마우스를 올렸을 때 읽어 줄 좌표. 차트마다 한 칸이고 `<figure data-life>` 가
   그 첨자를 들고 있습니다. **SVG 속성에 넣지 않습니다** — 111분기짜리가 스물몇
   개면 HTML 이 통째로 무거워집니다. */
let LIFES=[];
/* 차트가 들어갈 칸의 실제 폭. **`render()` 에서 목록 `<ul>` 을 재서 넣습니다** —
   차트는 그 안에 여백 없이 들어가므로 같은 값입니다. 이게 있어야 `1년` 을 눌러도
   차트가 카드를 꽉 채웁니다(전에는 분기 수로만 폭을 정해서 1년이 374px 짜리
   토막으로 나왔습니다). 못 재면 900px 카드 기준값으로 갑니다. */
let LIFEW=0;        // 분기 이름표 (lifeOf 가 씁니다)
let TICKERS={};
// 일별 종가는 수량·평균가·추정 수익률 계산과 분리합니다. 공급처가 없으면
// 실제 공시 가격만 표시하고, 말풍선에도 종가라고 부르지 않습니다.
let PRICE_SERIES={};
let PRICE_ASOF="";

// TITAN.prices에는 자체 종가 JSON 주소를 설정합니다. 공급처 조건은 CLAUDE.md에
// 기록합니다. 외부 공급자 요청·API 키는 방문자 화면에 넣지 않습니다.
function acceptPrices(book){
  if(!book||book.method!=="split-adjusted-close"||!book.series)return;
  for(const [key,series] of Object.entries(book.series)){
    if(!/^[A-Z0-9-]+$/.test(key)||!series||series.currency!=="USD"
       ||typeof series.ticker!=="string"||!Array.isArray(series.values))continue;
    const byDate=new Map();
    for(const o of series.values){
      if(!Array.isArray(o)||!/^\d{4}-\d{2}-\d{2}$/.test(o[0])||!Number.isFinite(o[1])||o[1]<=0)continue;
      const ms=Date.parse(o[0]);
      if(Number.isFinite(ms)&&new Date(ms).toISOString().slice(0,10)===o[0])byDate.set(o[0],[o[0],o[1]]);
    }
    const clean=[...byDate.values()].sort((a,b)=>a[0].localeCompare(b[0]));
    if(clean.length)PRICE_SERIES[key]={ticker:series.ticker.replace(/[^A-Za-z0-9.^=-]/g,""),values:clean};
  }
  PRICE_ASOF=Object.values(PRICE_SERIES).map(s=>s.values.at(-1)[0]).sort().at(-1)||"";
}


/* ── 섹터 ────────────────────────────────────────────────────
   **SEC 가 회사마다 업종 코드(SIC)를 매겨 둡니다.** `scripts/fetch_sectors.py`
   가 주 1회 받아 `data/titans/sectors.json` 에 저장한 것을 읽습니다.
   못 받았거나 모르는 회사면 그 자리를 **비웁니다** — 틀린 섹터를 적는 것보다
   안 적는 것이 낫습니다. */
let SECTORS={};

/* 이름표는 **회사가 아니라 코드로 답니다.** 회사마다 적으면 매니저를 더 넣을
   때마다 표가 늘어나고, 사람이 붙어야 하는 표는 결국 낡습니다(9-3의 티커와
   같은 이유). 네 자리에 없으면 앞 두 자리(대분류)로 떨어지고, 그것도 없으면
   SEC 가 적어 보낸 영문 설명을 그대로 씁니다. */
const SIC4={
  "1040":["금·광업","Gold Mining"],      "1311":["원유·가스","Oil & Gas"],
  "1531":["주택건설","Homebuilding"],    "2086":["음료","Beverages"],
  "2080":["음료","Beverages"],           "2084":["주류","Wine & Spirits"],
  "2111":["담배","Tobacco"],             "2834":["제약","Pharmaceuticals"],
  "2836":["바이오","Biotech"],           "2911":["석유·정유","Oil Refining"],
  "3571":["컴퓨터","Computers"],         "3674":["반도체","Semiconductors"],
  "3711":["자동차","Automobiles"],       "3721":["항공우주","Aerospace"],
  "3728":["항공우주","Aerospace"],       "4011":["철도","Railroads"],
  "4512":["항공","Airlines"],            "4513":["물류","Logistics"],
  "4812":["통신","Telecom"],             "4813":["통신","Telecom"],
  "4832":["방송","Broadcasting"],        "4833":["방송","Broadcasting"],
  "4841":["케이블TV","Cable TV"],        "5812":["외식","Restaurants"],
  "5961":["전자상거래","E-commerce"],    "6020":["은행","Banks"],
  "6021":["은행","Banks"],               "6022":["은행","Banks"],
  "6035":["은행","Banks"],               "6036":["은행","Banks"],
  "6141":["소비자금융","Consumer Finance"], "6199":["금융서비스","Financial Services"],
  "6211":["증권","Brokerage"],           "6311":["생명보험","Life Insurance"],
  "6321":["건강보험","Health Insurance"], "6324":["건강보험","Health Insurance"],
  "6331":["손해보험","P&C Insurance"],   "6411":["보험중개","Insurance Brokers"],
  "6798":["리츠","REITs"],               "7320":["신용평가","Credit Ratings"],
  "7370":["소프트웨어·IT","Software & IT"], "7371":["소프트웨어·IT","Software & IT"],
  "7372":["소프트웨어·IT","Software & IT"], "7373":["소프트웨어·IT","Software & IT"],
  "7374":["소프트웨어·IT","Software & IT"], "7389":["기업서비스","Business Services"],
  "7812":["영화·미디어","Film & Media"], "8092":["의료서비스","Health Services"],
};
/* 대분류는 **구간으로 적습니다.** 항목을 여든 줄 늘어놓는 것보다 짧고,
   빠진 코드가 생기지 않습니다. */
const SIC2=[
  [ 1, 9,"농림수산","Agriculture"],   [10,14,"광업·에너지","Mining & Energy"],
  [15,17,"건설","Construction"],      [20,20,"식품","Food"],
  [21,21,"담배","Tobacco"],           [22,23,"섬유·의류","Textiles & Apparel"],
  [24,25,"목재·가구","Wood & Furniture"], [26,27,"제지·인쇄","Paper & Printing"],
  [28,28,"화학·제약","Chemicals & Pharma"], [29,29,"석유·정유","Oil Refining"],
  [30,32,"소재","Materials"],         [33,34,"금속","Metals"],
  [35,35,"기계","Machinery"],         [36,36,"전자·전기","Electronics"],
  [37,37,"운송장비","Transport Equipment"], [38,38,"정밀기기","Instruments"],
  [39,39,"기타 제조","Manufacturing"], [40,47,"운송·물류","Transportation"],
  [48,48,"통신","Telecom"],           [49,49,"유틸리티","Utilities"],
  [50,51,"도매","Wholesale"],         [52,59,"소매","Retail"],
  [60,62,"금융","Financial"],         [63,64,"보험","Insurance"],
  [65,66,"부동산","Real Estate"],     [67,67,"지주·투자","Holding & Investment"],
  [70,79,"서비스","Services"],        [80,80,"헬스케어","Healthcare"],
  [81,89,"서비스","Services"],  [90,99,"기타","Other"],
];
function sectorOf(r){
  const v=SECTORS[r.key.split("|")[0]];
  if(!v||!v.sic) return "";
  const four=SIC4[v.sic];
  if(four) return LANG==="ko"?four[0]:four[1];
  const g=parseInt(String(v.sic).slice(0,2),10);
  for(const [lo,hi,ko,en] of SIC2) if(g>=lo&&g<=hi) return LANG==="ko"?ko:en;
  /* 표에 없는 코드. SEC 가 적어 보낸 설명을 그대로 씁니다 — 영어지만
     빈칸보다는 낫고, 어떤 코드를 표에 더할지도 이걸 보면 압니다. */
  return v.desc||"";
}

const LOGO={
  "037833":{h:"000000",t:"Apple",d:"M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"},
  "025816":{h:"2E77BC",t:"American Express",d:"M16.015 14.378c0-.32-.135-.496-.344-.622-.21-.12-.464-.135-.81-.135h-1.543v2.82h.675v-1.027h.72c.24 0 .39.024.478.125.12.13.104.38.104.55v.35h.66v-.555c-.002-.25-.017-.376-.108-.516-.06-.08-.18-.18-.33-.234l.02-.008c.18-.072.48-.297.48-.747zm-.87.407l-.028-.002c-.09.053-.195.058-.33.058h-.81v-.63h.824c.12 0 .24 0 .33.05.098.048.156.147.15.255 0 .12-.045.215-.134.27zM20.297 15.837H19v.6h1.304c.676 0 1.05-.278 1.05-.884 0-.28-.066-.448-.187-.582-.153-.133-.392-.193-.73-.207l-.376-.015c-.104 0-.18 0-.255-.03-.09-.03-.15-.105-.15-.21 0-.09.017-.166.09-.21.083-.046.177-.066.272-.06h1.23v-.602h-1.35c-.704 0-.958.437-.958.84 0 .9.776.855 1.407.87.104 0 .18.015.225.06.046.03.082.106.082.18 0 .077-.035.15-.08.18-.06.053-.15.07-.277.07zM0 0v10.096L.81 8.22h1.75l.225.464V8.22h2.043l.45 1.02.437-1.013h6.502c.295 0 .56.057.756.236v-.23h1.787v.23c.307-.17.686-.23 1.12-.23h2.606l.24.466v-.466h1.918l.254.465v-.466h1.858v3.948H20.87l-.36-.6v.585h-2.353l-.256-.63h-.583l-.27.614h-1.213c-.48 0-.84-.104-1.08-.24v.24h-2.89v-.884c0-.12-.03-.12-.105-.135h-.105v1.036H6.067v-.48l-.21.48H4.69l-.202-.48v.465H2.235l-.256-.624H1.4l-.256.624H0V24h23.786v-7.108c-.27.135-.613.18-.973.18H21.09v-.255c-.21.165-.57.255-.914.255H14.71v-.9c0-.12-.018-.12-.12-.12h-.075v1.022h-1.8v-1.066c-.298.136-.643.15-.928.136h-.214v.915h-2.18l-.54-.617-.57.6H4.742v-3.93h3.61l.518.602.554-.6h2.412c.28 0 .74.03.942.225v-.24h2.177c.202 0 .644.045.903.225v-.24h3.265v.24c.163-.164.508-.24.803-.24h1.89v.24c.194-.15.464-.24.84-.24h1.176V0H0zM21.156 14.955c.004.005.006.012.01.016.01.01.024.01.032.02l-.042-.035zM23.828 13.082h.065v.555h-.065zM23.865 15.03v-.005c-.03-.025-.046-.048-.075-.07-.15-.153-.39-.215-.764-.225l-.36-.012c-.12 0-.194-.007-.27-.03-.09-.03-.15-.105-.15-.21 0-.09.03-.16.09-.204.076-.045.15-.05.27-.05h1.223v-.588h-1.283c-.69 0-.96.437-.96.84 0 .9.78.855 1.41.87.104 0 .18.015.224.06.046.03.076.106.076.18 0 .07-.034.138-.09.18-.045.056-.136.07-.27.07h-1.288v.605h1.287c.42 0 .734-.118.9-.36h.03c.09-.134.135-.3.135-.523 0-.24-.045-.39-.135-.526zM18.597 14.208v-.583h-2.235V16.458h2.235v-.585h-1.57v-.57h1.533v-.584h-1.532v-.51M13.51 8.787h.685V11.6h-.684zM13.126 9.543l-.007.006c0-.314-.13-.5-.34-.624-.217-.125-.47-.135-.81-.135H10.43v2.82h.674v-1.034h.72c.24 0 .39.03.487.12.122.136.107.378.107.548v.354h.677v-.553c0-.25-.016-.375-.11-.516-.09-.107-.202-.19-.33-.237.172-.07.472-.3.472-.75zm-.855.396h-.015c-.09.054-.195.056-.33.056H11.1v-.623h.825c.12 0 .24.004.33.05.09.04.15.128.15.25s-.047.22-.134.266zM15.92 9.373h.632v-.6h-.644c-.464 0-.804.105-1.02.33-.286.3-.362.69-.362 1.11 0 .512.123.833.36 1.074.232.238.645.31.97.31h.78l.255-.627h1.39l.262.627h1.36v-2.11l1.272 2.11h.95l.002.002V8.786h-.684v1.963l-1.18-1.96h-1.02V11.4L18.11 8.744h-1.004l-.943 2.22h-.3c-.177 0-.362-.03-.468-.134-.125-.15-.186-.36-.186-.662 0-.285.08-.51.194-.63.133-.135.272-.165.516-.165zm1.668-.108l.464 1.118v.002h-.93l.466-1.12zM2.38 10.97l.254.628H4V9.393l.972 2.205h.584l.973-2.202.015 2.202h.69v-2.81H6.118l-.807 1.904-.876-1.905H3.343v2.663L2.205 8.787h-.997L.01 11.597h.72l.26-.626h1.39zm-.688-1.705l.46 1.118-.003.002h-.915l.457-1.12zM11.856 13.62H9.714l-.85.923-.825-.922H5.346v2.82H8l.855-.932.824.93h1.302v-.94h.838c.6 0 1.17-.164 1.17-.945l-.006-.003c0-.78-.598-.93-1.128-.93zM7.67 15.853l-.014-.002H6.02v-.557h1.47v-.574H6.02v-.51H7.7l.733.82-.764.824zm2.642.33l-1.03-1.147 1.03-1.108v2.253zm1.553-1.258h-.885v-.717h.885c.24 0 .42.098.42.344 0 .243-.15.372-.42.372zM9.967 9.373v-.586H7.73V11.6h2.237v-.58H8.4v-.564h1.527V9.88H8.4v-.507"},
  "02079K":{h:"4285F4",t:"Google",d:"M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"},
  "191216":{h:"D00013",t:"Coca-Cola",d:"M16.813 8.814s-.45.18-.973.756c-.524.577-.828 1.225-.603 1.397.087.066.287.079.65-.25a2.864 2.864 0 00.766-1.063c.234-.57.16-.833.16-.84m2.863 1.038c-.581-.299-1.006-.664-1.448-.89-.422-.216-.695-.307-1.036-.261a1.057 1.057 0 00-.14.035s.176.6-.523 1.607c-.708 1.022-1.35 1.015-1.533.734-.191-.296.056-.9.468-1.437.432-.562 1.19-1.028 1.19-1.028s-.241-.148-.835.19c-.58.326-1.577 1.107-2.502 2.423-.926 1.316-1.11 2.04-1.242 2.61-.132.57-.012 1.18.62 1.18s1.368-.964 1.576-1.299c.386-.624.637-1.581.112-1.45-.259.065-.468.351-.6.627a2.683 2.683 0 00-.19.554 2.185 2.185 0 00-.513.298 3.788 3.788 0 00-.486.43s.002-.456.365-1.194c.364-.737 1.03-1.074 1.408-1.106.34-.027.783.262.408 1.327-.375 1.065-1.483 2.36-2.646 2.376-1.073.015-1.776-1.355-.282-3.745C13.501 9.19 15.441 8.38 16.07 8.29c.63-.09.835.187.835.187a2.709 2.709 0 011.197-.197c.77.052 1.364.596 2.15.979-.205.195-.4.4-.575.592m3.454-.89c-.533.342-1.27.652-1.979.586-.179.185-.371.4-.563.634 1.228.243 2.305-.519 2.877-1.167A3.82 3.82 0 0024 8.248a4.792 4.792 0 01-.869.714m-1.636 3.462a.268.268 0 00.023-.051.124.124 0 00-.113-.108c-.117-.005-.277.017-.695.48a6.303 6.303 0 00-.89 1.263c-.24.438-.337.764-.2.848a.199.199 0 00.146.015c.093-.022.199-.11.36-.295.075-.088.158-.212.258-.349.277-.376.973-1.563 1.111-1.803m-4.349.504c.07-.182.159-.541-.026-.682-.199-.15-.705.201-.708.561-.003.369.357.535.443.559.05.013.066.01.09-.029a3.284 3.284 0 00.201-.409m-.383.67a1.531 1.531 0 01-.348-.222 1.116 1.116 0 01-.26-.317c-.008-.012-.015-.003-.023.008-.007.01-.039.039-.309.434-.27.396-.684 1.216-.31 1.355.241.09.641-.331.86-.61a5.21 5.21 0 00.402-.614c.012-.023 0-.029-.012-.034m4.258.947c-.102.163-.218.476.117.281.41-.236.994-1.123.994-1.123h.265a8.88 8.88 0 01-.803 1.054c-.415.46-.922.879-1.28.837-.416-.048-.286-.596-.286-.596s-.596.635-1.01.59c-.557-.062-.387-.751-.387-.751s-.63.774-1.06.75c-.673-.04-.504-.859-.316-1.436.1-.308.193-.55.193-.55s-.067.017-.21.038c-.076.011-.212.019-.212.019s-.28.495-.505.792c-.224.297-1.178 1.322-1.74 1.117-.518-.19-.346-.984-.044-1.615.44-.92 1.68-2.243 2.396-2.068.741.18.017 1.532.017 1.532s0 .005.007.009c.015.005.054.01.143-.008a1.605 1.605 0 00.271-.08s.746-1.561 1.569-2.583c.823-1.02 2.465-2.78 3.11-2.354.156.105.086.465-.126.902a2.891 2.891 0 01-.291.078c.142-.258.236-.475.264-.627.097-.528-1.135.585-2.015 1.78a16.594 16.594 0 00-1.409 2.28 3.86 3.86 0 00.454-.324 13.002 13.002 0 001.118-1.043 12.169 12.169 0 00.951-1.098 2.58 2.58 0 00.28-.029 12.054 12.054 0 01-1.05 1.24c-.35.355-.73.737-1.061 1.015a8.84 8.84 0 01-.931.691s-.77 1.553-.351 1.652c.246.06.732-.69.732-.69s.635-.967 1.017-1.404c.522-.593.97-.936 1.42-.942.261-.005.415.273.415.273l.123-.19h.757s-1.414 2.398-1.527 2.579m2.111-5.58c-.533.341-1.27.651-1.979.585-.18.185-.371.4-.564.634 1.229.243 2.305-.518 2.878-1.167A3.82 3.82 0 0024 8.248a4.792 4.792 0 01-.869.714m-10.63 1.177h-.72l-.407.658h.72zm-3.41 2.277c.307-.42 1.152-1.891 1.152-1.891a.124.124 0 00-.112-.108c-.117-.006-.312.034-.7.519-.387.485-.688.87-.907 1.272-.24.438-.346.747-.207.831a.205.205 0 00.144.015c.09-.022.208-.113.369-.298a5.57 5.57 0 00.262-.34m-3.863-1.99c-.199-.15-.705.201-.708.56-.003.369.456.482.515.484a.09.09 0 00.05-.01.06.06 0 00.024-.027 3.483 3.483 0 00.146-.325c.07-.183.158-.541-.027-.682m-.3 1.27a1.678 1.678 0 01-.39-.18.812.812 0 01-.279-.309c-.007-.012-.015-.003-.022.008-.007.01-.047.061-.318.458-.27.398-.672 1.21-.296 1.35.24.09.644-.334.864-.612a7.24 7.24 0 00.455-.681c.009-.024 0-.03-.014-.034m5.88.244h.263s-1.321 1.912-2.068 1.823c-.416-.049-.293-.563-.293-.563s-.585.685-1.123.546c-.487-.125-.172-.936-.172-.936-.056.022-1.111 1.211-1.853.926-.776-.3-.373-1.296-.225-1.595.125-.253.263-.499.263-.499s-.119.034-.195.051l-.186.04s-.367.596-.591.894c-.225.297-1.178 1.32-1.74 1.117-.562-.204-.423-.99-.107-1.615.512-1.012 1.726-2.256 2.458-2.068.739.189.127 1.388.127 1.388s.147.019.5-.222c.507-.346 1.176-1.277 1.901-1.167.342.051.66.4.225 1.064-.139.213-.372.403-.55.215-.111-.118-.014-.33.103-.477a.457.457 0 01.39-.179s.12-.273-.185-.269c-.247.005-.871.58-1.223 1.16-.323.533-.813 1.441-.322 1.639.451.182 1.309-.836 1.706-1.37.397-.533 1.302-1.742 2.062-1.79.261-.017.417.221.417.221l.088-.139h.759s-1.43 2.387-1.542 2.567c-.088.141-.204.46.117.281.322-.178.996-1.043.996-1.043m-.414 3.824a3.144 3.144 0 00-1.908-.557 1.17 1.17 0 00-.93.504c-.29-.505-.862-.815-1.747-.808-1.43.016-2.849.676-3.972.675-1.077 0-1.863-.677-1.837-1.88.047-2.109 1.83-4.009 3.16-4.864.767-.49 1.409-.637 1.828-.59.306.034.674.388.442.909-.341.761-.812.699-.795.335.01-.237.168-.386.286-.469a.582.582 0 01.278-.068c.068-.057.117-.474-.429-.337-.546.137-1.21.676-1.84 1.371-.63.696-1.61 2.011-1.852 3.392-.113.64-.039 1.808 1.48 1.795 1.287-.01 3.185-.859 4.929-.841a3.34 3.34 0 011.725.472c.451.278.992.684 1.184.961"},
  "060505":{h:"012169",t:"Bank of America",d:"M15.194 7.57c.487-.163 1.047-.307 1.534-.451-1.408-.596-3.176-1.227-4.764-1.625-.253.073-1.01.271-1.534.434.541.162 2.328.577 4.764 1.642zm-8.896 6.785c.577.343 1.19.812 1.786 1.209 3.952-3.068 7.85-5.432 12.127-6.767-.596-.307-1.119-.578-1.787-.902-2.562.65-6.947 2.4-12.126 6.46zm-.758-6.46c-2.112.974-4.331 2.31-5.54 3.085.433.199.866.361 1.461.65 2.671-1.805 4.764-2.905 5.594-3.266-.595-.217-1.154-.361-1.515-.47zm8.066.234c-.686-.379-3.068-1.263-4.71-1.642-.487.18-1.173.451-1.642.65.595.162 2.815.758 4.71 1.714.487-.235 1.173-.523 1.642-.722zm-3.374 1.552c-.56-.27-1.173-.523-1.643-.74-1.425.704-3.284 1.769-5.63 3.447.505.27 1.047.595 1.624.92 1.805-1.335 3.627-2.598 5.649-3.627zm1.732 8.825c3.79-3.249 9.113-6.407 12.036-7.544a48.018 48.018 0 00-1.949-1.155c-3.771 1.246-8.174 4.007-12.108 7.129.667.505 1.371 1.028 2.02 1.57zm2.851-.235h-.108l-.18-.27h-.109v.27h-.072v-.596h.27c.055 0 .109 0 .145.036.054.019.072.073.072.127 0 .108-.09.162-.198.162zm-.289-.343c.09 0 .199.018.199-.09 0-.072-.072-.09-.144-.09h-.163v.18zm-.523.036c0-.289.235-.523.541-.523.307 0 .542.234.542.523a.543.543 0 01-.542.542.532.532 0 01-.54-.542m.107 0c0 .235.199.433.451.433a.424.424 0 100-.848c-.27 0-.45.199-.45.415"},
};
/* 마크가 없을 때 쓰는 글자.
   **회사 형태를 뜻하는 낱말을 먼저 버립니다.** 안 버리면 Chevron Corporation 이
   'CC', Chubb Limited 가 'CL' 이 되어 회사가 아니라 법인 형태를 가리킵니다. */
const SUFFIX=/^(INC|INCORPORATED|CORP|CORPORATION|CO|COMPANY|LTD|LIMITED|PLC|LLC|LP|NV|SA|AG|HOLDINGS|HLDGS|GROUP|GRP|NEW|DEL|THE)$/i;
function monogram(name){
  const w=String(name).replace(/[^A-Za-z ]/g," ").trim().split(/\s+/)
    .filter(x=>x.length>1&&!SUFFIX.test(x));
  if(!w.length) return String(name).replace(/[^A-Za-z]/g,"").slice(0,2).toUpperCase()||"?";
  return (w.length>1?w[0][0]+w[1][0]:w[0].slice(0,2)).toUpperCase();
}
/* ══ 머리글의 투자자 이름표 ════════════════════════════════════════
   **글자만 있는 제목은 어느 투자자의 화면인지 늦게 읽힙니다.** 그래서
   이름 앞에 네모 하나를 두고, 이름만 `--ink`(제일 진한 잉크) 로 떼어 놓고
   나머지 설명은 `--ink-3` 으로 물립니다. **색을 새로 만들지 않았습니다** —
   이미 쓰는 잉크 세 단계 그대로입니다(재료표의 "색을 늘리지 마세요").

   기본은 **머리글자 타일**입니다. 진짜 로고 그림이 필요하면 투자자 파일의
   `window.TITAN.mark` 에 저장소 안 경로를 한 줄 적으면 됩니다 —
   `LIVE`·`STATS`·`SUPPORT` 와 같은 요령이라 **비우면 타일로 돌아갑니다.**
   그림을 못 받아도 `onerror` 가 같은 타일로 떨어지므로 화면이 비지 않습니다.

   **머리글자는 늘 영어 이름에서 뽑습니다.** `monogram()` 이 A-Z 만 보므로
   한글 이름을 주면 `?` 가 나옵니다. 그리고 이름표는 언어를 따라 바뀌면
   안 됩니다 — 같은 투자자의 같은 표식입니다. */
function titanMark(){
  const src=String(TT.mark||"").trim(), mono=monogram(TT.name.en||TT.slug||"");
  if(src) return `<span class="tmark img" aria-hidden="true"><img src="${esc(src)}" alt=""`
    +` onerror="this.closest('.tmark').classList.remove('img');this.replaceWith('${mono}')"></span>`;
  return `<span class="tmark" aria-hidden="true">${mono}</span>`;
}
/* 사전의 `tagline` 에 **이름 자리**를 통째로 넘깁니다. 언어마다 이름이 앞에
   오기도 뒤에 오기도 하므로, 문장을 쪼개지 않고 이름만 감싸는 쪽이 안전합니다. */
function taglineHTML(){
  return titanMark()+`<span class="ttext">`
    +tx("tagline",`<b class="tname">${esc(tName())}</b>`)+`</span>`;
}

/* 뒤로 물러나는 순서: 바깥 그림 → 저장소의 simple-icons → 글자 타일.
   그래서 바깥 서버가 죽어도 화면은 이 기능을 켜기 전 모습 그대로가 된다. */
function localMark(r){
  const g=LOGO[r.key.split("|")[0]];
  if(g) return `<span class="mk"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"`
    +` style="fill:#${g.h}"><path d="${g.d}"/></svg></span>`;
  return `<span class="mk mono" aria-hidden="true">${monogram(r.name)}</span>`;
}
function markHTML(r){
  const url=(window.MARKS&&window.MARKS.url)||"";
  const fall=localMark(r);
  if(url){
    /* 미국 종목이면 ISIN 을 즉석에서 계산하고(표가 필요 없다),
       아니면 표에서 티커를 찾는다. 둘 다 없으면 바깥에 묻지 않는다. */
    const isin=usISIN(r.cusip), tk=TICKERS[r.cusip];
    const src = isin ? url.replace("{idType}","isin").replace("{id}",isin)
              : tk   ? url.replace("{idType}","symbol").replace("{id}",encodeURIComponent(tk))
              : null;
    if(src){
      return `<span class="mk img" aria-hidden="true"><img src="${src}" alt="" loading="lazy"`
        +` onerror="this.parentNode.outerHTML='${fall.replace(/'/g,"&#39;").replace(/"/g,"&quot;")}'"></span>`;
    }
  }
  return fall;
}

/* ══ 추정 매수 평균가 ═══════════════════════════════════════════════
   13F 에는 체결가가 없습니다. 있는 것은 분기말의 **금액과 주식수**뿐이고,
   나누면 그 분기말 가격이 나옵니다. 그래서 이렇게 어림합니다.

     분기마다 늘어난 주식수를  (직전 분기말 + 이번 분기말) / 2  로 사들였다고 보고
     이동평균으로 이어 붙입니다. 팔면 평균단가는 그대로 두고 원가만 비례해서 줄입니다.

   **추정입니다.** 실제로는 분기 중 아무 날에나 샀으므로 크게 빗나갈 수 있습니다.
   각주에 그렇게 적어 두었고, 화면에도 '추정'이라고 씁니다.

   ── 액면분할이 제일 큰 함정입니다 ──────────────────────────────
   2020년 8월 애플 4:1 때 주식수가 245M → 944M 으로 뜁니다. 이걸 '샀다'로 세면
   **추정 평균단가가 $39.59 대신 $213.33 이 되어 수익률이 +631% 대신 +36% 로
   나옵니다.** 실측으로 확인한 숫자입니다 — 분할을 안 잡으면 이 화면은 거짓말을 합니다.

   분할은 공시 자체에서 찾습니다: 주식수가 f 배로 뛰면서 가격이 꼭 1/f 로 내려간 분기.
   **정수 배수만 인정합니다.** 1.5 배를 후보에 넣었더니 '55% 더 산 분기'(애플 2016-06)와
   '주식을 크게 늘린 분기'(레너드 2026-03)가 분할로 잡혔습니다. 정수만 두면
   현재 26묶음에서 다섯 건이 정확히 잡히고 오탐이 없습니다 —
   애플 ×4(2020-09) · 아멕스 ×3(2000-06) · 코카콜라 ×2(2012-09) ·
   무디스 ×2(2005-06) · 다비타 ×2(2013-09).
══════════════════════════════════════════════════════════════════ */
const SPLITF=[2,3,4,5,6,7,8,10,15,20];
/* 가격 쪽 여유가 넉넉한 것은 분기 중에 시세가 움직이기 때문입니다 —
   애플은 분할과 같은 분기에 주가가 27% 올랐습니다. */
function splitFactor(rShares,rPrice){
  let best=null;
  for(const f of SPLITF){
    if(Math.abs(rShares/f-1)<.30 && Math.abs(rPrice/f-1)<.30){
      if(best===null||Math.abs(rShares/f-1)<Math.abs(rShares/best-1)) best=f;
    }
  }
  return best;
}
/* 묶음 하나의 일생을 처음부터 되짚어 평균단가를 만든다.
   전량 매도하면 0 에서 다시 시작한다 — 3년 전에 팔고 다시 산 종목의
   평균단가에 옛 매수가 섞이면 안 된다. */
function costBasis(snaps,key){
  let held=0,cost=0,prevP=null,first=null;
  for(let i=0;i<snaps.length;i++){
    const a=snaps[i].get(key);
    if(!a||a.shares<=0||a.value<=0){ held=0;cost=0;prevP=null;first=null; continue; }
    const p=a.value/a.shares;
    if(first===null) first=i;
    if(held>0&&prevP){
      const f=splitFactor(a.shares/held, prevP/p);
      if(f){ held*=f; prevP/=f; }
    }
    if(held===0){ cost=a.shares*p; held=a.shares; }
    else if(a.shares>held){ cost+=(a.shares-held)*((prevP+p)/2); held=a.shares; }
    else if(a.shares<held){ cost*=a.shares/held; held=a.shares; }
    prevP=p;
  }
  return {avg:held>0?cost/held:null, first, last:prevP};
}

/* 한 묶음의 공시 이력 — 금액 ÷ 주식수는 공시 기준 분기말 가격입니다.
   일별 종가나 실제 매매일·체결가가 아닙니다.
   **과거를 오늘 기준으로 맞춥니다** — 분할이 나오면 그때까지 쌓은 값의 가격은
   ÷f, 주식수는 ×f. 안 그러면 분할이 '699M주 매수'로 찍혀 거짓말이 됩니다.

   **전량 매도하면 끊습니다.** 3년 전에 팔고 다시 산 종목의 선을 이어 그리면
   중간에 없었던 사실이 사라집니다(보유 연차를 세는 규칙과 같은 자리). */
function lifeOf(snaps,key){
  const out=[];
  let held=null,prevP=null;
  for(let i=0;i<snaps.length;i++){
    const a=snaps[i].get(key);
    if(!a||a.shares<=0||a.value<=0){
      /* 마지막 보유 가격을 매도가로 쓰지 않습니다. 다음 공시는 수량이
         사라졌다는 것만 알려 주므로 가격 없는 매도 기록을 한 번만 남깁니다. */
      if(held) out.push({q:QS[i],gi:i,p:null,sh:0,dn:-held,first:false,exit:true});
      held=null;prevP=null;continue;
    }
    const p=a.value/a.shares;
    if(held&&prevP){
      const f=splitFactor(a.shares/held, prevP/p);
      /* **직전 주식수도 같이 늘려야 합니다.** 지난 분기들만 고치고 `held` 를 그대로
         두면 이번 분기 증감이 `944M - 245M = +699M` 으로 잡혀 **액면분할이 사상
         최대의 매수로 그려집니다**(애플 2020-09 에서 실제로 그랬습니다).
         늘려 두면 `944M - 980M = -36M` 으로, 그 분기에 실제로 판 만큼만 남습니다. */
      if(f){ for(const o of out){ if(o.p!==null)o.p/=f; o.sh*=f; o.dn*=f; } held*=f; SPLITS.push({key,q:QS[i],f}); }
    }
    /* **`gi` 는 전체 분기 목록에서의 자리입니다.** 배열 첨자로 가로 위치를
       잡으면 안 됩니다 — 뱅크오브아메리카는 2010-09 에 전량 매도하고 2017-09
       에 다시 샀는데, 첨자로 그리면 두 점이 **바로 옆에 붙어 7년이 통째로
       사라집니다**(실제로 그렇게 그려지고 있었습니다). */
    out.push({q:QS[i], gi:i, p, sh:a.shares, dn:held?a.shares-held:0, first:!held});
    held=a.shares; prevP=p;
  }
  return out;
}

/* 주당 가격. 금액(money)과 자릿수가 다르다 — $66.0B 와 $289.36 은 다른 자입니다. */
/* 차트 안에서 쓰는 주식수. **`K`·`M`·`B` 로 줄이되 소수 둘째 자리까지**
   적습니다 (사용자 요청 — "너무 디테일하게 쓰는데 대충 줄여줘").
   `+136,373,000` 은 아홉 글자라 12px 간격의 막대 위에서 이웃을 밀어내고,
   정확한 자릿수는 말풍선이 아니라 **목록 줄**이 이미 말합니다.
   단위 글자는 언어를 안 탑니다 — `K`·`M` 은 한국어 화면에서도 그대로 씁니다. */
function compShares(n){
  const a=Math.abs(n);
  if(a>=1e9) return (n/1e9).toFixed(2)+"B";
  if(a>=1e6) return (n/1e6).toFixed(2)+"M";
  if(a>=1e3) return (n/1e3).toFixed(2)+"K";
  return Math.round(n).toLocaleString(LOCALE);
}

/* 가로축 눈금의 날짜. **`26 Q1` 이 아니라 `2026.03.31` 입니다** (사용자 요청) —
   `Q1` 은 주린이에게 통하는 말이 아니고, 13F 는 실제로 그날의 스냅샷입니다.
   두 언어가 같은 꼴을 씁니다(숫자뿐이라 번역할 것이 없습니다). */
const axDate=iso=>String(iso).replace(/-/g,".");

const usd=n=>"$"+n.toLocaleString(LOCALE,{minimumFractionDigits:2,maximumFractionDigits:2});

/* 수익률은 자릿수가 커진다. 100% 안쪽은 소수 한 자리, 그 밖은 정수. */
function retPct(r){
  const v=r*100, a=Math.abs(v);
  const n=a<100?v.toFixed(1):Math.round(v).toLocaleString(LOCALE);
  return (v>0?"+":v<0?"\u2212":"")+String(n).replace("-","")+"%";
}

/* 가격 자료는 종목별 실제 관측값만 사용합니다. 일별 종가가 연결되면 투자자의
   첫 매수 이전·전량 매도 이후도 보여 줍니다. 13F 계산에는 이 가격을 넣지 않습니다. */
function chartBody(r,li){
  const all=r.life||[],g0=winStart(),end=QS.length-1,frame=chartWindow();
  const M=all.filter(o=>o.q>=frame.start&&o.q<=frame.end),held=M.filter(o=>!o.exit);
  const move=o=>o.first?(o.gi===0?0:o.sh):o.dn;
  const mv=M.map(o=>o.q<=frame.start?0:move(o));
  let bought=0,sold=0;
  all.filter(o=>o.q<=frame.start).forEach(o=>{const n=move(o);if(n>0)bought++;else if(n<0)sold++;});
  const prior=(bought||sold)?`<b class="lifeprior">${tx("lifePrior",bought,sold)}</b>`:"";
  const W=LIFEW||806,LEFT=10,RIGHT=10,PADT=18,H1=150,PADB=30;
  const t0=Date.parse(frame.start),t1=Date.parse(frame.end);
  const xd=q=>LEFT+(Date.parse(q)-t0)/Math.max(1,t1-t0)*(W-LEFT-RIGHT);
  const xg=g=>PRICE_ASOF?xd(QS[g]):LEFT+(g-g0)/(Math.max(1,end-g0))*(W-LEFT-RIGHT);
  const daily=PRICE_SERIES[r.cusip]||PRICE_SERIES[r.key];
  const prices=daily?daily.values.filter(o=>o[0]>=frame.start&&o[0]<=frame.end)
    .map(o=>({q:o[0],p:o[1],x:xd(o[0]),first:false}))
    :held.map(o=>({q:o.q,p:o.p,x:xg(o.gi),first:o.first}));
  const ps=prices.map(o=>o.p),rawLo=ps.length?Math.min(...ps):0,rawHi=ps.length?Math.max(...ps):1;
  const pad=(rawHi-rawLo)*.08||rawHi*.06||1,lo=rawLo-pad,hi=rawHi+pad;
  const y=p=>PADT+H1-(p-lo)/(hi-lo)*H1;
  const traded=mv.some(Boolean),BARMAX=W<430?27:34.5;
  // 전량 매도도 위로. 분기말에 가는 막대를 세우지 않고 해당 분기 전체를 채웁니다.
  const zero=PADT+H1+(traded?BARMAX+29:0),H=zero+PADB;
  const maxMove=Math.max(...mv.map(Math.abs),1);
  const height=v=>Math.max(2,Math.abs(v)/maxMove*BARMAX);
  const bars=M.map((o,i)=>{
    if(!mv[i])return "";
    const begin=Math.max(LEFT,xg(o.gi-1)),finish=Math.min(W-RIGHT,xg(o.gi));
    const bx=begin+.5,bw=Math.max(.5,finish-begin-1),h=height(mv[i]);
    return `<rect x="${bx.toFixed(2)}" y="${(zero-h).toFixed(2)}" width="${bw.toFixed(2)}" height="${h.toFixed(2)}" data-quarter="${o.q}" data-shares="${Math.abs(mv[i])}" class="${mv[i]>0?"bUp":"bDn"}"/>`;
  }).join("");
  // 이름표는 실제 텍스트 폭에 여유를 둬서 선택합니다. 모바일에서도 글자를 줄이지 않습니다.
  const labels=[],candidates=M.map((o,i)=>({o,v:mv[i]})).filter(t=>t.v).sort((a,b)=>Math.abs(b.v)-Math.abs(a.v));
  const labelLimit=W<430?2:Math.max(2,Math.floor(W/140));
  for(const t of candidates){
    const text=(t.v>0?"+":"−")+compShares(Math.abs(t.v));
    const width=text.length*6.7+8,cx=Math.max(LEFT+width/2,Math.min(W-RIGHT-width/2,(Math.max(LEFT,xg(t.o.gi-1))+xg(t.o.gi))/2));
    if(labels.length>=labelLimit||labels.some(l=>Math.abs(l.cx-cx)<(l.width+width)/2+8))continue;
    labels.push({text,cx,width,yy:zero-height(t.v)-7,cls:t.v>0?"up":"down"});
  }
  const marks=labels.map(l=>`<text x="${l.cx.toFixed(2)}" y="${l.yy.toFixed(2)}" text-anchor="middle" class="bLab ${l.cls}">${l.text}</text>`).join("");
  const line=prices.map((o,i)=>`${i&&!o.first?"L":"M"}${o.x.toFixed(2)} ${y(o.p).toFixed(2)}`).join(" ");
  const point=prices.length===1?`<circle cx="${prices[0].x}" cy="${y(prices[0].p)}" r="2.6" class="pDot"/>`:"";
  const tickCount=Math.max(2,Math.min(5,Math.floor((W-LEFT-RIGHT)/128)+1));
  const ticks=Array.from({length:tickCount},(_,i)=>{
    const g=Math.round(g0+(end-g0)*i/(tickCount-1)),anc=i===0?"start":i===tickCount-1?"end":"middle";
    const aim=new Date(t0+(t1-t0)*i/(tickCount-1));
    const day=PRICE_ASOF?(i===0?frame.start:i===tickCount-1?frame.end:
      new Date(Date.UTC(aim.getUTCFullYear(),Math.floor(aim.getUTCMonth()/3)*3+3,0)).toISOString().slice(0,10)):QS[g];
    return `<text x="${(PRICE_ASOF?xd(day):xg(g)).toFixed(2)}" y="${H-7}" text-anchor="${anc}" class="axL">${axDate(day)}</text>`;
  }).join("");
  const pts=M.map((o,i)=>({x:xg(o.gi),y:o.exit?zero:y(o.p),q:o.q,p:o.p,mv:mv[i]}));
  const pricePts=prices.map(o=>({...o,y:y(o.p)}));
  LIFES[li]={r,pts,pricePts,daily:!!daily,ticker:daily?.ticker||"",top:PADT,bot:zero,left:LEFT,right:W-RIGHT};
  const svg=`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${title(r.name)}">
    <path d="${line}" class="pLine"/>${point}
    ${traded?`<line x1="${LEFT}" y1="${zero}" x2="${W-RIGHT}" y2="${zero}" class="zero"/>`:""}
    ${bars}${marks}${ticks}
    <g class="cross" pointer-events="none"><line class="cx" y1="${PADT}" y2="${zero}"/><circle class="cdot" r="3.2"/></g>
  </svg>`;
  return {svg,prior};
}


/* 기간 버튼 — `1년 5년 10년 15년`. 값은 **분기 수**입니다.
   `3년`과 `전체`는 사용자 판단으로 뺐습니다 (2026-09-17). */
const LR=[4,20,40,60];
let LRANGE=60;                     // 기본은 15년. 모든 줄이 함께 씁니다.

/* **한 줄만 따로 놀게 하지 않습니다.** 기간은 그 종목의 성질이 아니라 *보는 방법*
   이라 26줄이 제각각이면 위아래를 견줄 수 없습니다. 4번 대시보드에서 위·아래
   버튼을 묶어 둔 것과 같은 판단입니다. */
function loadRange(){
  try{ const v=+localStorage.getItem("bk.range");
       if(LR.includes(v)) LRANGE=v; }catch(e){}
}
function saveRange(){ try{ localStorage.setItem("bk.range",LRANGE) }catch(e){} }

/* **버튼을 흐리게 만들지 않습니다.** 예전에는 "이력보다 긴 기간"을 못 누르게
   했는데, 이제 가로축이 **그 종목의 이력이 아니라 달력**이라(아래 `winStart`)
   어느 기간이든 뜻이 있습니다 — 처브를 `15년` 으로 보면 15년짜리 축 오른쪽 끝에
   2년치 선만 그려지고, 그게 바로 **언제 들어왔는지**입니다(사용자 요청).
   목록에 있는 26줄은 전부 지금 보유 중이라 어느 창에서도 값이 있습니다. */
function rangeBar(){
  return `<div class="seg mini lifeseg" role="group" aria-label="${tx("lifeSpanLab")}">`
    + LR.map((q,i)=>`<button type="button" data-q="${q}"`
        + ` aria-pressed="${q===LRANGE}">${tx("lifeSpans")[i]}</button>`).join("")
    + `</div>`;
}

/* 창의 왼쪽 끝 — **전체 분기 목록에서** 셉니다. 종목마다 다른 자리에서 시작하면
   줄끼리 가로축이 안 맞아 "언제 들어왔나"를 견줄 수 없습니다. */
/* N년은 N×4개 간격이므로 경계 관측점까지 N×4+1개가 필요합니다. */
const winStart=()=>Math.max(0, QS.length-1-LRANGE);
function chartWindow(){
  if(!PRICE_ASOF)return {start:QS[winStart()],end:QS.at(-1)};
  const finish=new Date(PRICE_ASOF+"T00:00:00Z"),start=new Date(finish);
  const month=start.getUTCMonth();start.setUTCFullYear(start.getUTCFullYear()-LRANGE/4);
  if(start.getUTCMonth()!==month)start.setUTCDate(0);
  return {start:start.toISOString().slice(0,10),end:PRICE_ASOF};
}

/* 말풍선은 그림 **바깥**에 있는 형제입니다. 그림만 갈아 끼울 때도 같이 넣어야
   합니다 — 한 번 빠뜨려서 기간 버튼을 누르면 말풍선이 사라졌습니다. */
const TIP=`<b class="lifetip" aria-live="polite" hidden></b>`;

function chartHTML(r){
  const L=r.life||[];
  if(!L.length&&!PRICE_SERIES[r.key]) return `<p class="lifenote">${tx("lifeThin")}</p>`;
  const li=LIFES.length; LIFES.push(null);      // 자리를 먼저 잡고 chartBody 가 채웁니다
  const o=chartBody(r,li);
  return `<figure class="life" data-life="${li}">
    ${rangeBar()}
    <div class="lifescroll">${o.svg}${o.prior}${TIP}</div>
  </figure>`;
}

/* 기간을 바꾸면 그림만 갈아 끼웁니다. 줄 전체를 다시 그리면
   펼쳐 둔 것이 접힙니다. */
function drawLife(fig){
  const li=+fig.dataset.life, st=LIFES[li];
  if(!st) return;
  const r=st.r, o=chartBody(r,li);
  fig.querySelector(".lifescroll").innerHTML=o.svg+o.prior+TIP;
  clearLife(fig);
  fig.querySelectorAll(".lifeseg button").forEach(b=>
    b.setAttribute("aria-pressed", String(+b.dataset.q===LRANGE)));
  settleLife(fig);
}


function rowHTML(r,rank,maxW){
  const tag=classTag(r), sec=sectorOf(r);
  const barW=Math.max(0,Math.min(100,r.w/maxW*100));
  const tickW=r.wPrev===null?null:Math.max(0,Math.min(100,r.wPrev/maxW*100));

  /* 가운데 둘째 칸 — 이번 분기에 **몇 주** 사고팔았나. **숫자 한 줄**이고
     색이 방향을 말합니다(사용자 요청 — `BUY`/`SELL` 스티커 삭제).

     **한 줄에 색깔 숫자가 둘이 되는 것**(증감과 수익률)이 원래 이 스티커를
     둔 이유였는데, 둘은 부호가 다릅니다 — 증감은 `+`/`−` 가 붙고 수익률은
     `%` 가 붙습니다. 그리고 열 머리글이 `이번 분기`·`추정 수익률` 이라고
     이미 갈라 적고 있습니다. */
  let dir="", num;
  if(r.isNew){ num=r.back?tx("evBack"):tx("evNew"); }
  else if(r.flat||!r.dn){ num=tx("same"); }
  else{
    const up=r.isNew||r.dn>0;
    dir=up?" up":" down";
    num=(up?"+":"\u2212")+shortShares(Math.abs(r.isNew?r.shares:r.dn));
  }
  const act=`<span class="act${dir}">${num}</span>`;

  /* 가운데 셋째 칸 — 추정 수익률. 못 쓰는 자리가 둘 있고, 둘 다 말로 밝힙니다.
     칸이 좁으므로 여기서는 짧게 적고 긴 설명은 각주가 합니다. */
  let gain;
  if(r.preData) gain=`<span class="note">${tx("noRetOld")}</span>`;
  else if(r.freshIn||!r.avgCost) gain=`<span class="note">${tx("noRetNew")}</span>`;
  else{
    const g=r.nowPrice/r.avgCost-1;
    gain=`<span class="ret ${g>=0?"up":"down"}">${retPct(g)}</span>`;
  }

  /* 줄을 누르면 그 종목의 일생이 펼쳐집니다. `<details>` 를 쓰므로 키보드와
     여닫이가 공짜로 따라옵니다 — 아래 '더 보기' 와 같은 어휘입니다.
     **비중 막대와 직전 분기 표식은 `<summary>` 안**에 둡니다. `<li>` 에 두면
     펼친 차트 높이까지 막대가 늘어나 줄이 아니라 기둥처럼 보입니다. */
  return `<li class="row"><details class="lf">
    <summary class="rowline">
    <span class="bar" style="width:${barW.toFixed(2)}%"></span>
    ${tickW===null?"":`<span class="tick" style="left:${tickW.toFixed(2)}%"></span>`}
    <div class="rowin">
      <div class="who">
        <b class="caret"></b>
        ${markHTML(r)}
        <span class="rk">${rank}</span>
        <span class="nm">${title(r.name)}${tag?`<span class="cls">${tag}</span>`:""}</span>
        ${sec?`<span class="sec">${sec}</span>`:""}
      </div>
      <div class="mid">
        <span class="hold">${shortShares(r.shares)}</span>
        ${act}
        ${gain}
      </div>
      <div class="amt">
        <span class="val">${money(r.value)}</span>
        <span class="wt">${weightPct(r.w).replace("<","&lt;")}</span>
      </div>
    </div>
    </summary>
    ${chartHTML(r)}
  </details></li>`;
}

/* 마우스·터치 위치에 점선과 가장 가까운 실제 관측값을 표시합니다.
   분기 자료만 있으면 종가로 부르지 않습니다. 말풍선은 창 안에 맞춥니다. */
function readLife(fig, clientX){
  const L=LIFES[+fig.dataset.life]; if(!L) return;
  const svg=fig.querySelector("svg"), g=fig.querySelector(".cross");
  const out=fig.querySelector(".lifetip");
  const box=svg.getBoundingClientRect();
  /* SVG 는 `width` 속성과 `viewBox` 가 같은 값이라 보통 1:1 인데, 좁은 화면에서
     줄어들 수 있으므로 실제 폭으로 환산합니다. */
  const sx=(clientX-box.left)*(svg.viewBox.baseVal.width/(box.width||1));
  if(!L.pricePts.length){clearLife(fig);return;}
  if(sx<L.pricePts[0].x-2||sx>L.pricePts.at(-1).x+2){clearLife(fig);return;}
  let best=0;
  for(let i=1;i<L.pricePts.length;i++)
    if(Math.abs(L.pricePts[i].x-sx)<Math.abs(L.pricePts[best].x-sx)) best=i;
  const t=L.pricePts[best],cursor=Math.max(L.left,Math.min(L.right,sx));
  g.classList.add("on");
  g.querySelector(".cx").setAttribute("x1",cursor); g.querySelector(".cx").setAttribute("x2",cursor);
  g.querySelector(".cdot").setAttribute("cx",t.x); g.querySelector(".cdot").setAttribute("cy",t.y);
  g.querySelector(".cdot").setAttribute("visibility",t.p===null?"hidden":"visible");
  /* **값은 짚은 자리에 띄웁니다** (사용자 요청 — 구석에 두니 "도저히 못 알아보겠다").
     그림 안이 아니라 그림 위에 얹는 HTML 이라 바탕을 깔 수 있고 잘리지 않습니다.
     `.lifescroll` 이 기준 상자라 옆으로 끌면 말풍선도 같이 따라갑니다. */
  out.innerHTML=`<em>${fdate(t.q)}</em><br>${tx(L.daily?"close":"impliedPrice")} ${usd(t.p)}${L.ticker?" · "+L.ticker:""}`;
  out.hidden=false;
  /* 오른쪽 끝 점은 말풍선이 그림 밖으로 나가므로 왼쪽으로 뒤집습니다. */
  const sc=fig.querySelector(".lifescroll");
  const tw=out.offsetWidth, th=out.offsetHeight;
  /* **눈에 보이는 창을 기준으로 뒤집습니다.** 그림 전체 폭으로 재면, 옆으로
     끌어 놓은 28년치 차트에서 말풍선이 그림 안에는 있는데 화면 밖으로 나갑니다. */
  const vr=sc.scrollLeft+sc.clientWidth, vl=sc.scrollLeft;
  let lx=t.x+12;
  if(lx+tw>vr) lx=t.x-12-tw;          // 오른쪽에 자리가 없으면 왼쪽으로
  if(lx<vl) lx=Math.min(t.x+12, vr-tw); // 왼쪽에도 없으면 창 안으로 밀어 넣는다
  out.style.left=Math.max(0,lx)+"px";
  /* 점 위에 얹되 그림 위로 삐져나가지 않게 합니다. */
  out.style.top=Math.max(2,Math.min(t.y-th-8, L.bot-th))+"px";
}
function clearLife(fig){
  const g=fig.querySelector(".cross"); if(g) g.classList.remove("on");
  const out=fig.querySelector(".lifetip"); if(out){ out.hidden=true; out.innerHTML=""; }
}

/* **손가락으로 탭하면 값이 남아 있어야 합니다.** 예전에는 손을 떼는 순간
   (`pointerup`) 지웠는데, 탭은 누르자마자 떼는 것이라 값이 떴다가 바로 사라져
   **휴대폰에서는 아무것도 못 읽었습니다**(실측에서 잡음). 지금은 마우스만
   빠져나갈 때 지우고, 손가락은 **다른 데를 누를 때** 지웁니다. */
let TAPWIRED=false;
function wireTapAway(){
  if(TAPWIRED) return;
  TAPWIRED=true;
  document.addEventListener("pointerdown",e=>{
    const mine=e.target.closest&&e.target.closest("figure.life");
    document.querySelectorAll("figure.life").forEach(f=>{ if(f!==mine) clearLife(f); });
  },true);
}

function wireLife(ul){
  if(!ul) return;
  wireTapAway();
  ul.querySelectorAll("figure.life").forEach(fig=>{
    const sc=fig.querySelector(".lifescroll"); if(!sc) return;
    sc.addEventListener("pointermove",e=>readLife(fig,e.clientX));
    sc.addEventListener("pointerdown",e=>readLife(fig,e.clientX));
    sc.addEventListener("pointerleave",e=>{ if(e.pointerType==="mouse") clearLife(fig); });
    sc.addEventListener("pointercancel",()=>clearLife(fig));
  });
  /* 기간 버튼. **한 줄에서 누르면 모든 줄이 같이 옮겨 갑니다** — 기간은 그
     종목의 성질이 아니라 보는 방법이라, 줄마다 달라지면 위아래를 견줄 수 없습니다. */
  ul.querySelectorAll(".lifeseg").forEach(seg=>{
    seg.addEventListener("click",e=>{
      const b=e.target.closest("button[data-q]");
      if(!b||b.disabled) return;
      const q=+b.dataset.q;
      if(q===LRANGE) return;
      LRANGE=q; saveRange();
      document.querySelectorAll("figure.life").forEach(drawLife);
    });
  });

  ul.querySelectorAll("details.lf").forEach(d=>{
    d.addEventListener("toggle",()=>{ if(d.open) settleLife(d); });
  });
}

/* 접혀 있는 동안은 폭이 0 이라 미리 옮길 수 없습니다. 그래서 **열리는 순간**과
   **기간을 바꾼 직후**에 이것을 부릅니다. */
function settleLife(root){
  const sc=root.querySelector(".lifescroll");
  if(!sc) return;
  sc.scrollLeft=sc.scrollWidth;
}

/* 각주. 분할 목록과 '집계 전' 종목은 자료에서 오므로 **새 분기가 들어오면
   글도 따라 바뀝니다** — 새 분할이 잡히면 저절로 실리고, 집계 전 종목을
   팔면 그 이름이 저절로 빠집니다. */
function paintFoot(B){
  const el=document.getElementById("footbody");
  if(el) el.innerHTML=tx("foot",FIRSTY,B?B.splits:null,B?B.preNames:null)
    .concat(PRICE_ASOF?[tx("priceNote",PRICE_ASOF)]:[]).map(s=>`<p>${s}</p>`).join("");
}

function render(){
  const el=id=>document.getElementById(id);
  el("brand").textContent=tx("brand");
  el("tagline").innerHTML=taglineHTML();
  el("mobileguide").textContent=tx("mobileGuide");
  el("tradebasis").textContent=tx("tradeBasis");
  el("foothead").textContent=tx("footTitle");
  /* 각주를 두 번 그립니다. **자료가 없어도 각주는 나와야 하므로** 한 번은
     맨 앞에서 예시 없이 그리고, `build()` 뒤에 분할·집계 전 목록을 채워
     다시 그립니다. */
  paintFoot(null);
  el("legend").textContent=tx("prevTick");
  el("qhead").textContent=tx("quarterHead");
  if(!RAW){ el("stamp").textContent=LOADED?tx("noData"):""; return; }

  FIRSTY=String(RAW.quarters[0].period).slice(0,4);
  const B=build(), T=tallyOf(B);
  paintFoot(B);
  el("stamp").innerHTML=`${tx("asOf",fdate(B.cur.period))}<br>${tx("filedOn",fdate(B.cur.filed))}`;

  /* 직전 분기가 없으면 비교할 대상이 없다. 그대로 그리면 전 종목이 '신규'로
     찍혀 거짓말이 되므로 이번 분기 칸을 통째로 접는다. */
  if(!B.prv){ el("quarter").hidden=true; }
  else{
  el("tally").innerHTML=[
    ["kNew",T.nw,"up"],["kAdd",T.add,"up"],["kTrim",T.trim,"down"],
    ["kHold",T.hold,""],["kOut",T.out,"down"]
  ].map(([k,n,c])=>`<div class="${n?c:""}"><span class="n">${n}</span><span class="k">${tx(k)}</span></div>`).join("");
  el("says").innerHTML=says(B,T).map(s=>`<p>${s}</p>`).join("");

  /* 사건은 접히지 않는다. 이번 분기 신규가 26위($400만)라 크기로 접으면 사라진다. */
  const evs=[];
  for(const r of B.list.filter(x=>x.isNew))
    evs.push(`<div class="ev in"><span class="tag">${r.back?tx("evBack"):tx("evNew")}</span><span class="nm">${title(r.name)}</span><span class="sub">${money(r.value)}</span></div>`);
  for(const r of B.out)
    evs.push(`<div class="ev out"><span class="tag">${tx("evOut")}</span><span class="nm">${title(r.name)}</span><span class="sub">${tx("heldFor")} ${tx("yr",Math.round(r.years*10)/10)} · ${money(r.value)}</span></div>`);
  el("events").innerHTML=evs.join("");
  el("events").hidden=!evs.length;
  el("quarter").hidden=false;
  }

  /* 목록 */
  el("bookhead").textContent=`${tx("positions",B.list.length)} · ${money(B.tc)}`;
  el("bookcap").textContent=tx("costArrow",fdate(B.cur.period));
  /* 열 이름은 **줄마다 되풀이하지 않고 머리에 한 번만** 적습니다 — 26줄이면
     같은 말이 78번 나오고, 라벨이 숫자보다 자리를 더 차지합니다(4번 성적표에서
     이미 같은 판단을 했습니다). 줄마다 바뀌는 `BUY`/`SELL` 만 줄 안에 둡니다. */
  el("c1").textContent=tx("colShares");
  el("c2").textContent=tx("colQtr");
  el("c3").textContent=tx("colRet");
  el("c4").textContent=tx("colVal");
  /* 상위 10종목을 펴고 **나머지는 접습니다 — 지우는 것이 아닙니다.**
     전체 종목 수와 총액은 제목에 그대로 둡니다 — 10개가 전부인 것처럼 보이면
     화면이 거짓말을 합니다. 막대 폭은 접힌 줄도 1위 기준으로 그려서, 펼쳤을 때
     위아래가 같은 자로 읽힙니다. */
  const maxW=B.list[0]?B.list[0].w:1;
  const top=B.list.slice(0,10), rest=B.list.slice(10);
  /* `chartHTML` 이 여기서 좌표를 쌓으므로 그리기 직전에 비웁니다 — 언어를
     바꿀 때도 `render()` 가 다시 도니까 안 비우면 계속 불어납니다. */
  LIFES=[];
  el("top").innerHTML=top.map((r,i)=>rowHTML(r,i+1,maxW)).join("");
  el("rest").innerHTML=rest.map((r,i)=>rowHTML(r,i+11,maxW)).join("");
  wireLife(el("top")); wireLife(el("rest"));
  const shown=top.reduce((s,r)=>s+r.value,0)/B.tc*100;
  const fold=el("fold");
  if(rest.length){
    el("foldttl").textContent=tx("foldOpen",rest.length);
    fold.hidden=false;
    /* **펼치면 '상위 10종목만' 이 거짓말이 됩니다.** 접힘을 열어 둔 채로 그 줄을
       그대로 두면 화면이 자기 말을 어깁니다. 여는 순간 문장을 바꿉니다. */
    const cut=()=>el("bookcut").textContent=
      fold.open?tx("allShown",B.list.length):tx("topOnly",top.length,pct(shown));
    cut(); fold.ontoggle=cut;
  }else{
    fold.hidden=true; fold.open=false; fold.ontoggle=null;
    el("bookcut").textContent="";
  }
  el("book").hidden=false;
  /* **폭은 카드를 펼친 뒤에 잽니다.** 위에서 재려고 했더니 그때는 `#book` 이
     아직 `hidden` 이라 `clientWidth` 가 0 이었고, 390px 화면에서도 900px 짜리
     기본값으로 그려졌습니다(실측에서 잡음). 값이 달라졌으면 한 번 다시 그립니다 —
     이때는 줄이 다 접혀 있어 눈에 안 띕니다. */
  fitLife();
}

/* 차트가 들어갈 칸의 실제 폭을 재고, 달라졌으면 다시 그립니다. */
function fitLife(){
  const ul=document.getElementById("top");
  const w=ul&&ul.clientWidth;
  if(!w||Math.abs(w-LIFEW)<2) return;
  LIFEW=w;
  document.querySelectorAll("figure.life").forEach(drawLife);
}

function applyLang(lang,remember){
  LANG=D[lang]?lang:"en"; L10N=D[LANG]; LOCALE=pickLocale(LANG);
  if(remember){ try{ localStorage.setItem("dt.lang",LANG) }catch(e){} }
  const r=document.documentElement;
  r.setAttribute("lang",LANG); r.setAttribute("dir",L10N.dir||"ltr");
  const p=REDUP.has(LANG)?PAL.redUp:PAL.greenUp;
  r.style.setProperty("--up",p.up); r.style.setProperty("--down",p.down);
  r.style.setProperty("--up-rgb",p.upRGB); r.style.setProperty("--down-rgb",p.downRGB);
  document.title=tx("docTitle",tName(),TT.since);
  paintHead(); paintTabs(); render();
}
function paintHead(){
  const set=(sel,attr,val)=>{const e=document.head.querySelector(sel);if(e)e.setAttribute(attr,val)};
  const t=tx("docTitle",tName(),TT.since),d=tx("metaDesc",tName());
  set('meta[name="description"]',"content",d);
  set('meta[property="og:title"]',"content",t);
  set('meta[property="og:description"]',"content",d);
  set('meta[property="og:locale"]',"content",LANG==="ko"?"ko_KR":"en_US");
  set('meta[property="og:locale:alternate"]',"content",LANG==="ko"?"en_US":"ko_KR");
  const c=document.head.querySelector('link[rel="canonical"]');
  /* 언어는 같은 정적 페이지의 표시 전환입니다. 원본·실행 후·og:url의 대표
     주소를 맞춥니다. 투자자를 복제할 때는 head와 TT.slug를 함께 바꿉니다. */
  if(c) c.setAttribute("href",`https://itpaidoff.com/titans/${TT.slug}/`);
}
/* 언어를 바꾸면 글자가 바뀌므로 탭은 비우고 다시 그린다(본 사이트와 같은 예외). */
function paintTabs(){
  const box=document.getElementById("langtabs");
  box.innerHTML=Object.keys(D).map(k=>
    `<button type="button" data-lang="${k}" aria-pressed="${k===LANG}">${D[k].tab}</button>`).join("");
}
document.getElementById("langtabs").addEventListener("click",e=>{
  const b=e.target.closest("button[data-lang]"); if(!b)return;
  applyLang(b.dataset.lang,true);
  try{ if(window.track) track("lang",{lang:LANG}); }catch(err){}
});

/* 곁들이 표 둘(티커·섹터)은 있으면 좋고 없어도 그만입니다 — 못 받으면 그 줄만
   글자 타일이 되고 섹터 자리가 빌 뿐입니다. 그래서 따로 받고, 실패를 화면에
   알리지 않습니다. 투자자별 공시 파일만이 없으면 안 되는 파일입니다. */
const side=(url,take)=>fetch(url,{cache:"no-store"})
  .then(r=>r.ok?r.json():null)
  .then(j=>{
    if(j&&typeof j==="object")
      /* `_` 로 시작하는 키는 사람이 보라고 넣어 둔 것입니다(마지막으로 물어본 날). */
      for(const k in j) if(k[0]!=="_"&&j[k]) take(k,j[k]);
  })
  .catch(()=>{});


Promise.all([
  TT.prices?fetch(TT.prices,{cache:"no-store"}).then(r=>r.ok?r.json():null).then(acceptPrices).catch(()=>{}):Promise.resolve(),
  side("../../data/titans/tickers.json",(k,v)=>{ if(typeof v==="string") TICKERS[k]=v; }),
  side("../../data/titans/sectors.json",(k,v)=>{ if(v&&typeof v==="object") SECTORS[k]=v; }),
]).finally(()=>{
  fetch(TT.data,{cache:"no-store"})
    .then(r=>r.ok?r.json():null)
    .then(j=>{ RAW=(j&&Array.isArray(j.quarters)&&j.quarters.length)?j:null; })
    .catch(()=>{ RAW=null; })
    .finally(()=>{ LOADED=true; applyLang(pickLang(),false); });
});

/* 지난번에 고른 기간을 **첫 그림 전에** 읽습니다 — 뒤에 읽으면 전체로 한 번
   그렸다가 바뀌어 화면이 깜빡입니다. 값이 이상하면 그냥 전체로 갑니다. */
loadRange();
applyLang(pickLang(),false);

/* 창 크기가 바뀌면 차트도 다시 그립니다 — 안 그러면 휴대폰을 돌렸을 때
   차트만 옛 폭으로 남습니다. 잦게 부르면 111분기짜리를 스물몇 개 다시 그리므로
   멈춘 뒤에 한 번만 합니다. */
let RSZ=0;
addEventListener("resize",()=>{ clearTimeout(RSZ); RSZ=setTimeout(fitLife,160); });
setTimeout(()=>document.body.classList.add("settled"),1600);
