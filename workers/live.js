/**
 * Daniel's timing — 실시간 중계소 (Cloudflare Worker)
 *
 * 왜 필요한가
 *   브라우저는 CORS 때문에 야후·CNN 을 직접 못 부른다. GitHub Actions 로
 *   대신 받아 두는 방법은 써 봤는데, 예약 실행이 "10분마다"를 전혀 지키지
 *   않았다(실측: 연속 실행 간격 중앙값 16분, 최근에는 하루 3~4회).
 *   그래서 방문자가 페이지를 열 때 그 자리에서 받아오는 쪽으로 바꾼다.
 *
 * 무엇을 주는가
 *   { fetched, open, quotes: { spx, ndx, vix, fng } }
 *   각 항목은 { v: 값, d: "YYYY-MM-DD", t: "…Z" } 또는 아예 없음.
 *   하나가 막혀도 나머지는 그대로 준다 — 받은 것만 담는다.
 *
 * 올리는 법 (계정 만들기 포함 5분, 명령어 없음)
 *   1. dash.cloudflare.com 가입 → 왼쪽 Compute(Workers) → Create
 *   2. "Start from Hello World" → Deploy → Edit code
 *   3. 이 파일 내용을 통째로 붙여넣고 Deploy
 *   4. 주소(https://…​.workers.dev)를 복사해서 알려 주세요.
 *      index.html 의 window.LIVE.url 한 줄에 넣으면 켜집니다.
 *
 * 비용
 *   무료 요금제가 하루 10만 요청. 아래에서 60초 캐시를 걸어 두었으므로
 *   방문자가 아무리 많아도 야후에는 분당 1회만 나간다.
 */

const YAHOO = {
  spx: "SPY",
  ndx: "QQQ",
  vix: "%5EVIX",          /* ^VIX */
};

/* 야후·CNN 둘 다 기본 UA 를 보고 막는다. 브라우저처럼 보이게 한다. */
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const iso = (sec) => new Date(sec * 1000).toISOString().replace(/\.\d+Z$/, "Z");
const day = (sec) => new Date(sec * 1000).toISOString().slice(0, 10);

async function grab(url, headers) {
  const r = await fetch(url, {
    headers: { "User-Agent": UA, Accept: "application/json,*/*", ...headers },
    /* 60초 동안은 클라우드플레어가 대신 답한다. 원천에 부담을 주지 않는다. */
    cf: { cacheTtl: 60, cacheEverything: true },
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

async function quote(symbol) {
  const j = await grab(
    `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}` +
    "?range=1d&interval=5m");
  const m = j.chart.result[0].meta;
  const price = m.regularMarketPrice;
  if (typeof price !== "number") throw new Error("regularMarketPrice 없음");
  const stamp = m.regularMarketTime || Math.floor(Date.now() / 1000);
  const per = (m.currentTradingPeriod || {}).regular || {};
  const now = Math.floor(Date.now() / 1000);
  return {
    v: Math.round(price * 100) / 100,
    d: day(stamp),
    t: iso(stamp),
    open: !!(per.start <= now && now <= per.end),
  };
}

/* CNN 본진. 장중에도 값이 바뀐다. GitHub 러너에서는 418(봇 차단)이었는데,
   클라우드플레어에서는 되는지 실제로 열어 봐야 안다. 막히면 이 항목만
   빠지고, 화면은 하루 한 번짜리 값을 그대로 쓴다. */
async function fearGreed() {
  const j = await grab(
    "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
    { Referer: "https://edition.cnn.com/markets/fear-and-greed" });
  const f = j.fear_and_greed;
  if (!f || typeof f.score !== "number") throw new Error("score 없음");
  const t = f.timestamp ? new Date(f.timestamp).toISOString() : new Date().toISOString();
  return { v: Math.round(f.score), d: t.slice(0, 10), t: t.replace(/\.\d+Z$/, "Z") };
}

export default {
  async fetch(request) {
    const head = {
      "Content-Type": "application/json; charset=utf-8",
      /* 공개 시세다. 비밀이 없으므로 누가 불러도 상관없다. */
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=60",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: head });

    const quotes = {};
    const failed = [];
    const jobs = Object.entries(YAHOO).map(async ([key, sym]) => {
      try { quotes[key] = await quote(sym); }
      catch (e) { failed.push(key + ": " + e.message); }
    });
    jobs.push((async () => {
      try { quotes.fng = await fearGreed(); }
      catch (e) { failed.push("fng: " + e.message); }
    })());
    await Promise.all(jobs);

    const body = {
      fetched: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
      open: Object.values(quotes).some((q) => q && q.open),
      quotes,
    };
    if (failed.length) body.failed = failed;   /* 무엇이 막혔는지 눈으로 본다 */
    return new Response(JSON.stringify(body, null, 2), { headers: head });
  },
};
