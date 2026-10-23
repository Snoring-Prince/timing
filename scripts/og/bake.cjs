// 공유 그림 굽기 — node scripts/og/bake.cjs olympics
// scripts/og/<이름>.html 을 1200×630 으로 찍어 <이름>/og.png 에 씁니다(손으로 돌리는 도구, 예약 작업 없음).
// Pretendard 를 못 쓰면 다른 글꼴로 구운 그림이 올라가지 않게 멈춥니다.
const path=require('node:path'),fs=require('node:fs');
const {chromium}=require('playwright');
const name=process.argv[2];
if(!/^[a-z]+$/.test(name||''))throw new Error('usage: node scripts/og/bake.cjs <name>');
const root=path.resolve(__dirname,'../..'),src=path.join(__dirname,name+'.html'),out=path.join(root,name,'og.png');
const exe=['/opt/pw-browsers/chromium-1194/chrome-linux/chrome'].find(f=>fs.existsSync(f));
(async()=>{
  const browser=await chromium.launch(exe?{executablePath:exe}:{});
  const page=await browser.newPage({viewport:{width:1200,height:630},deviceScaleFactor:1});
  await page.goto('file://'+src,{waitUntil:'load'}).catch(()=>{});
  await page.evaluate(()=>document.fonts.ready);
  const ok=await page.evaluate(()=>{
    const c=document.createElement('canvas').getContext('2d'),w=f=>{c.font='800 40px '+f;return c.measureText('같은 돈, 다섯 가지 선택').width;};
    return w('"Pretendard Variable"')!==w('"__no_such_font__"');
  });
  if(!ok){await browser.close();throw new Error('Pretendard Variable is not available; install it before baking');}
  await page.screenshot({path:out,clip:{x:0,y:0,width:1200,height:630}});
  await browser.close();
  console.log('wrote',path.relative(root,out),fs.statSync(out).size,'bytes');
})().catch(e=>{console.error(e.message);process.exit(1);});
