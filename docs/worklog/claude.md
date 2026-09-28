# Claude Code 일지

형식과 규칙은 `README.md`. **맨 위가 최신이다.** Claude 만 이 파일에 쓴다.

---

## 2026-09-28 · Claude · (이 PR)
애크먼(퍼싱 스퀘어) 화면 — 여섯 번째 투자자, 겹친 분기 합치기
- 파일: scripts/fetch_13f.py · scripts/titans/registry.py · scripts/tests/test_fetch_13f.py ·
  titans/pershing/index.html(새) · titans/index.html(카드) · data/titans/investors.json ·
  sitemap.xml · CLAUDE.md · docs/masters-13f.md · 이 일지
- 결과(PR #107): 하워드 휴즈 펀드 18,852,064 + 지주회사 9,000,000 = 합쳐 낸 2분기 27,852,064 (네 분기 모두).
- 규칙: predecessors 의 `merge: true` → 겹친 분기는 두 원본을 `combine()` 으로 더함. 같은 주식 수·금액
  (1% 안)이면 중복으로 한 번만(`merged_dups`). 정정은 낸 법인의 원본에만. 짝을 못 받으면 그 분기 안 씀.
- 넘김: 머지 뒤 Update 13F → 끝난 뒤 Update Titans Prices. 13F 로그에서 2025-06-30~2026-03-31 에
  `⊕ 예전 번호 공시 1건과 합침` 이 붙고 공시 총액 ✓ 인지, 하워드 휴즈가 27,852,064주인지 볼 것.

## 2026-09-28 · Claude · PR #107
애크먼 정찰 6차 — 겹친 분기의 하워드 휴즈
- 파일: scripts/probe_titans.py · CLAUDE.md · 이 일지
- 결과(PR #106): 새 번호 = 퍼싱 지주회사, 2분기는 그룹 전체(6곳 전부 퍼싱 계열) · 1분기와 이어짐.
  단 새 번호가 2025-06-30~2026-03-31 에 하워드 휴즈 한 종목을 따로 냄(두 번호가 같은 분기를 냄).
- 사용자 판단: 겹친 분기는 합치고 중복만 뺀다.
- 규칙: 이어짐 확인은 옛 번호가 멈춘 뒤의 첫 분기와 견줌(−274일 버그). 겹친 분기마다 둘 다
  있는 종목의 주식 수(옛·새·합)와 합쳐 낸 첫 분기(2026-06-30)의 주식 수를 찍음.
- 넘김: `pershing` 으로 Probe Titans. 합 ≈ 2분기면 더하기, 한쪽 ≈ 2분기면 한 번만. 그다음 등록 —
  fetch_13f 에 '겹친 분기 합치기'(predecessor 옵션)를 넣고 화면·카드·사이트맵.

## 2026-09-28 · Claude · PR #106
애크먼 정찰 5차 — 대신 신고자(PERSHING SQUARE INC.)
- 파일: scripts/probe_titans.py · CLAUDE.md · 이 일지
- 결과(PR #105): 에이온 AON · 리버티 C주 LBTYK 로 붙음. 6-30 종가가 공시 값과 소수까지 같음.
- 규칙: pershing 후보에 0002026053 을 더하고 옛 번호를 predecessor 로 — 이어짐 확인이 돈다.
  최신 분기 표지의 보고 종류·함께 실린 운용사·줄마다 다른 운용사 번호를 찍음.
- 넘김: Probe Titans 를 `pershing` 만으로 돌린 로그를 볼 것. HOLDINGS REPORT 이고 이어짐이
  테퍼처럼 높으면 등록 후보. COMBINATION 이면 줄마다 번호로 퍼싱 몫을 가를 수 있는지 판단.

## 2026-09-28 · Claude · PR #105
종류 글자 줄(CL A·CL C)을 이름 검색으로 찾기
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 결과(PR #104): NCLH·AXTA·HLF 붙음. 남은 에이온(`SHS CL A`)·리버티 C주(`COM CL C`).
- 규칙: OpenFIGI `/v3/search` 로 회사 이름 검색 → 미국 보통주 중 이름 끝 종류 글자가 공시와 같은
  하나만. 꼬리 없는 이름은 유일하고 A주일 때만. 붙인 것도 종가 대조 2%. 검색 장애는 그 줄만 고장.
  되돌려 다섯 가지 모두 검사가 잡는 것 확인. 검색 응답 모양은 짐작 — 거절되면 원본이 로그에 찍힘.
- 넘김: 머지 뒤 Update Titans Prices. 초록불이면 로그에서 G0403H108·G61188127 줄을 볼 것 —
  `AON`/`LBTYK` 로 붙었는지, `class search rejected · raw …` 면 원본을 보고 규칙을 고칠 것.
  빨간불(HTTP 400 등)이면 검색 요청 모양이 틀린 것.

## 2026-09-28 · Claude · PR #104
바우포스트 종가 — 이름 표기 차이 셋
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 결과(PR #103): 토름 붙음. 바우포스트 해외 5종목 짝 없음 — NCLH(OpenFIGI 이름 28자 잘림) ·
  AXTA(SYS/SYSTEMS) · HLF(`COM SHS` 를 보통주로 안 봄) · AON(`SHS CL A`) · LBTY C(`COM CL C`).
- 규칙: 앞부분 3글자 이상 겹치면 같은 낱말, 28자 이상 이름은 끝 낱말 빼고, `COM SHS` 보통주.
  종류 글자 줄(CL A/C)은 그대로 안 붙임. 되돌려 다섯 가지 모두 검사가 잡는 것 확인.
- 넘김: 머지 뒤 Update Titans Prices — NCLH·AXTA·HLF 가 붙는지(빨간불 없음이 정상).
  HLF 원본은 아직 못 봄 — 떨어지면 로그의 `fallback rejected · raw` 줄을 볼 것.

## 2026-09-28 · Claude · PR #103
토름 종가 대조 문턱 0.5% → 2%
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 결과(PR #102): 바우포스트 53분기 · 2022-12-31 부터 14분기에 `unit_by: prev-quarter` · 총액
  끊김 없음($6.11B→…→$5.42B). 종가 작업은 13F 저장보다 먼저 시작돼 바우포스트를 못 봄 —
  Update Titans Prices 를 한 번 더 누르면 됨. 토름은 +1.06%(코펜하겐 종가 환산으로 봄).
- 넘김: 머지 뒤 Update Titans Prices 한 번. `prices/baupost.json` 이 생기고 TRMD 가
  `unpriced` 에서 빠지는지 볼 것. 다음은 애크먼 대신 신고자 정찰.

## 2026-09-28 · Claude · PR #102
클라만(바우포스트) 화면 — 다섯 번째 투자자
- 파일: titans/baupost/index.html(새) · titans/index.html(카드) · data/titans/investors.json ·
  sitemap.xml · CLAUDE.md · docs/masters-13f.md · 이 일지
- 규칙: 13F 밖(부실채권·부동산·비상장)이 커서 "미국 상장 주식만" 을 글에 적음(숫자 없이).
  천 달러 단위 공시는 수집기 `unit_by` 가 직전 분기 가격으로 가림.
- 넘김: 머지 뒤 Update 13F → Update Titans Prices. 13F 로그에서 2023년 이후 분기에
  `unit_by: prev-quarter` 가 붙는지, 분기 총액이 1000배 튀지 않고 이어지는지 볼 것.
  토름 숫자(PR #101)는 다음 예약 주가 실행 로그에서 확인.

## 2026-09-28 · Claude · PR #101
토름 종가 대조 실패에 숫자를 남김
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 결과(PR #100): 해외 5종목 중 LBTYA·KRSP·XP·ALVO 붙음. TRMD(오크트리 1위)는
  종가 대조에서 떨어짐 — 얼마나 어긋났는지 로그에 없었음. 이제 이유에 종가·공시가·차이를 적음.
- 넘김: 머지 뒤 Update Titans Prices 로그의 `G89479102 TRMD: 알려진 상태 …` 줄에서 차이를 볼 것.
  1~2% 면 코펜하겐 종가 기준일 공산(티커는 맞음), 크면 다른 종목. 그 뒤 판단.
  다음은 애크먼 대신 신고자(PERSHING SQUARE INC., CIK 0002026053) 정찰.

## 2026-09-28 · Claude · PR #100
오크트리 종가 — 짝 없는 11종목
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 규칙: OpenFIGI 이름의 A주 꼬리(`-A`·`CLASS A`)만 뗌. 워런트는 둘째 종류로 안 셈.
  이름으로 붙인 티커는 분기말 종가가 공시 금액÷주식수와 0.5% 안일 때만.
  짝 없음(OpenFIGI 가 답했는데 없음 · 처음 보는 티커 404 · 종가 대조 실패)은
  `prices.json` 의 `unpriced` 에 적고 처음만 빨간불.
- 넘김: 머지 뒤 Update Titans Prices — 한 번은 빨간불(목록을 처음 적는 날)이 정상.
  로그에서 TRMD·LBTYA·XP·KRSP·ALVO 가 `N days` 로 붙었는지, 안 붙었으면
  `fallback rejected · raw` 줄을 볼 것. 그다음 실행이 초록불이어야 한다.

## 2026-09-28 · Claude · PR #99
오크트리 첫 수집의 빨간불 — 텍스트 원본에 붙은 XML 정정
- 파일: scripts/fetch_13f.py · scripts/tests/test_audit_regressions.py · CLAUDE.md · 이 일지
- 규칙: 원본이 pre-xml 인 분기의 XML 정정은 `original-pre-xml` 로 기록하고 초록불.
  원문을 못 받은 것(통신 실패)만 실패.
- 넘김: 머지 뒤 Update 13F → 초록불 확인, 그다음 Update Titans Prices(오크트리 종가).
  다음은 애크먼 대신 신고자(PERSHING SQUARE INC., CIK 0002026053) 정찰.

## 2026-09-28 · Claude · PR #98
막스(오크트리) 화면 — 네 번째 투자자
- 파일: titans/oaktree/index.html(새) · titans/index.html(카드) · data/titans/investors.json ·
  sitemap.xml · CLAUDE.md · docs/masters-13f.md · 이 일지
- 규칙: 13F 의 옵션·원금은 빼고 주식만 — 소개 글·카드에 적음(숫자 없이).
- 넘김: 머지 뒤 Update 13F → Update Titans Prices. 정정 66건이라 첫 수집에서
  모르는 amendmentType 이 나오면 빨간불 — 그 접수번호를 열어 볼 것.
  다음은 애크먼 대신 신고자(PERSHING SQUARE INC., CIK 0002026053) 정찰.

## 2026-09-28 · Claude · PR #97
ASML 종가 2차 — 실제 OpenFIGI 응답에 맞춤
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 규칙: 이름 비교에서 주식 종류 낱말(NY·REG·REGISTRY·SHS)과 HLDG 를 버림.
  종류는 securityType 'NY Reg Shrs' 로만(securityType2 는 'Depositary Receipt' 라 못 씀).
- 굳힘: 검사가 러너 로그의 원본 응답을 그대로 씀.
- 넘김: 머지 뒤 Update Prices → `N07059210 ASML: N days` 확인.

## 2026-09-28 · Claude · PR #96
ASML 종가 — 해외 종목 우회 규칙이 뉴욕 등록주를 받게
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 규칙: CINS 우회는 한 종류뿐인 본주 표기만(COM·SHS·ORD·N Y REGISTRY SHS·REG SHS·
  NAMEN AKT). 이름 비교에서 HLDG 를 버림. 못 붙이면 OpenFIGI 원본을 로그에 찍음.
- 넘김: 머지 뒤 Update Prices 를 눌러 초록불인지, 로그에 `N07059210 ASML: N days` 가
  찍히는지 확인. 빨간불이면 로그의 `fallback rejected · raw` 줄이 이유다.
  다음은 막스(오크트리) · 애크먼 대신 신고자 정찰.

## 2026-09-28 · Claude · PR #95
테퍼(애팔루사) 화면 · 예전 CIK 를 이어 붙이는 수집
- 파일: titans/appaloosa/index.html(새) · titans/index.html(카드) · data/titans/investors.json ·
  scripts/titans/registry.py · scripts/fetch_13f.py · titans/shared/investor.js(각주 출처) ·
  sitemap.xml · scripts/tests/test_fetch_13f.py · scripts/tests/test_13f_watch.py ·
  CLAUDE.md · docs/masters-13f.md · 이 일지
- 규칙: registry `predecessors` = 예전 CIK. 원문은 낸 법인 폴더에서. 겹치는 분기는 지금 번호.
- 굳힘: since 2013(예전 번호의 텍스트 시대는 안 읽음).
- 넘김: 머지 뒤 Update 13F → Update Prices. 실제 이음매(2015-12-31 → 2016-03-31) 확인.
  다음은 막스(오크트리) · 애크먼 대신 신고자 정찰.

## 2026-09-28 · Claude · PR #94
투자자 목록 /titans/ · 첫 화면 카드 02 를 목록으로 · 목록용 요약 파일
- 파일: titans/index.html · index.html · scripts/publish_titans.py(새) ·
  data/titans/summary.json(새, 봇이 만듦) · titans/shared/investor.js(맨 아래 링크) ·
  .github/workflows/update-13f.yml · .github/workflows/check-titans.yml · sitemap.xml ·
  scripts/tests/test_titans_summary.py(새) · scripts/tests/titans.test.cjs ·
  CLAUDE.md · docs/design-system.md · 이 일지
- 규칙: 목록·첫 화면 숫자는 summary.json 만 읽는다. 이름 표기는 파이썬·JS 두 벌을
  검사가 대조한다. 투자자를 더하면 목록 카드도 한 장.
- 굳힘: 리루 실제 자료 — 2023~24 여섯 분기 천 달러 단위를 unit_by 가 잡음.
- 넘김: 다음은 테퍼(옛 CIK 한 번 이어 붙이기) · 애크먼 대신 신고자 정찰.

## 2026-09-28 · Claude · PR #93
리루(히말라야 캐피털) 화면 · 애크먼 대신 신고자 확인 · 새 투자자 주가 대기
- 파일: titans/himalaya/index.html(새) · data/titans/investors.json · sitemap.xml ·
  scripts/fetch_prices.py · scripts/tests/test_prices.py · scripts/tests/titans.test.cjs ·
  CLAUDE.md · docs/masters-13f.md · 이 일지
- 규칙: 공시·주가 자료는 봇이 받는다(머지 뒤 Update 13F → Update Prices). 모든
  투자자 페이지를 한 검사가 훑는다.
- 굳힘: 정찰 run 36377898009 — 애크먼 2분기는 PERSHING SQUARE INC.(0002026053)가 대신 신고.
- 넘김: 리루 자료가 들어오면 실제 화면을 다시 잴 것. 그다음 `/titans/` 목록 · 테퍼.

## 2026-09-28 · Claude · PR #92
공시마다 금액 단위를 확인 · 애크먼 13F-NT 대신 낸 곳 찾기 · 막스 확정
- 파일: scripts/fetch_13f.py · scripts/probe_titans.py · scripts/tests/test_audit_regressions.py ·
  CLAUDE.md · docs/masters-13f.md · 이 일지
- 규칙: `unit_by()` = 직전 분기 같은 종목 가격과 비교(100배↑ 어긋남 + 10배 안 → 뒤집기),
  아니면 같은 시대 직전 분기 단위, 아니면 날짜. 버크셔 110쌍 그대로(검사).
- 굳힘: 정찰 run 36376757948 — 막스 확정(주식은 13F 의 절반), 애크먼 2분기는 13F-NT.
- 넘김: 머지 뒤 Probe Titans 한 번 → 애크먼 대신 신고한 운용사 이름. 그다음 리루 화면.

## 2026-09-28 · Claude · PR #91
정찰 2차 결과 반영 · 달리오 뺌 · 드러켄밀러 전 종목 · 하워드 막스 정찰
- 파일: scripts/probe_titans.py · .github/workflows/probe-titans.yml · CLAUDE.md ·
  docs/masters-13f.md · 이 일지
- 규칙: run 36375516285. 클라만 CIK 맞음. 테퍼 두 번호 이어짐 확인(같은 CFO 서명,
  34종목·금액 87/85% 이어짐). 드러켄밀러·클라만은 2023년 이후에도 천 달러 단위.
- 굳힘: 두 사람을 넣기 전에 공시마다 금액 단위를 재는 장치가 먼저다.
- 넘김: 머지 뒤 사용자가 Probe Titans 를 다시 누르면 오크트리 숫자와 애크먼의
  최근 13F 계열 제출이 나온다.

## 2026-09-28 · Claude · PR #90
정찰 1차 결과 반영 · 그린블라트→클라만 · 주가 파일을 투자자별로 나눔
- 파일: scripts/fetch_prices.py · titans/berkshire/index.html ·
  data/titans/prices/berkshire.json(새, 봇이 만듦) · .github/workflows/update-prices.yml ·
  .github/workflows/check-titans.yml · scripts/probe_titans.py ·
  .github/workflows/probe-titans.yml · scripts/tests/test_prices.py ·
  scripts/tests/test_13f_watch.py · scripts/tests/titans.test.cjs · CLAUDE.md ·
  docs/masters-13f.md · docs/design-system.md · 이 일지
- 규칙: prices.json 은 봇의 공유 창고, 화면은 `prices/<slug>.json`(그 투자자 최신
  보유만)을 받는다. `fetch_prices.py --publish` 가 받지 않고 다시 만든다.
  정찰 run 36369828081: 여섯 CIK 다 맞음. 그린블라트는 사용자 판단으로 뺌(클라만).
  테퍼는 두 CIK 를 잇는다(옛 번호는 한 번만).
- 굳힘: 드러켄밀러 총액 $0.0B(단위 의심, 확인 전) · 애크먼 2분기 공시 없음 —
  둘 다 등록 전에 확인. 매일 가격 덮어쓰기의 저장소 증가는 거의 0(7판 525KB).
- 넘김: 머지 뒤 사용자가 Probe Titans 를 다시 누르면 클라만 CIK·오닐 이름·
  드러켄밀러 금액÷주식수·테퍼 두 번호의 이어짐(겹치는 종목·금액 몫)이 나온다. 그다음 리루부터 한 명씩.

## 2026-09-28 · Claude · PR #89
대가들의 선택 여덟 명 확정 · 새 후보 여섯 곳 정찰 만듦
- 파일: scripts/probe_titans.py · .github/workflows/probe-titans.yml · CLAUDE.md ·
  docs/masters-13f.md · 이 일지
- 규칙: 갈래별로 고름(가치 버핏·리루 / 공식 그린블라트 / 성장 캐시 우드 / 거시 달리오·
  드러켄밀러 / 행동주의 애크먼 / 역발상 테퍼). 캐시 우드는 마지막. 르네상스·시타델·
  버리·파브라이 뺌. 달리오는 사용자 판단으로 넣음(9-14 의 뺀 이유를 뒤집음).
- 굳힘: 정찰 CIK 는 기억값 — 로그의 회사 이름으로 확인할 것. 두 번째 투자자 전에
  prices.json 을 투자자별로 나눈다.
- 넘김: 사용자가 Actions → Probe Titans 를 눌러야 다음으로 간다.

## 2026-09-26 · Claude · PR #88
첫 화면을 허브로 바꾸고 대시보드를 `/timing/` 으로 옮겼다
- 파일: index.html(새 허브) · timing/index.html(옮긴 대시보드) · sitemap.xml ·
  .github/workflows/update-data.yml · .github/workflows/check.yml ·
  scripts/check_about.py · scripts/tests/dashboard.test.cjs · CLAUDE.md · AGENTS.md ·
  다음에 할 일.md · 이 일지
- 규칙: 되돌릴 자리 `backup/v1.1`(889e1ce)을 먼저 찍었다. 허브 숫자는 방문자 자료에서
  읽고 VIX 는 안 쓴다. 네이버 소유확인 meta 는 뿌리에 있어야 한다.
- 굳힘: 그림 네 장은 사용자가 뺐다 — 코드는 `c7a00aa` 에 있다. 알람봇은 나중에
  한 번에(사용자). 토요일 `splitsFrom` 확인 끝(29/29, AXP·MCO 옛 분할 실림).
- 넘김: 머지 뒤 사용자가 Search Console 에 사이트맵 재제출·`/`·`/timing/` 색인 요청.
  허브용 공유 카드(og)는 아직 대시보드 것을 쓴다.

## 2026-09-23 · Claude · PR #84
연차보고서 대조는 **불가** 확정 — 여덟 해가 전부 업종별. 추정은 추정으로 둔다
- 파일: scripts/probe_annual.py · CLAUDE.md · 이 일지
- 규칙(실측, run 35883986339 · 10-K 8해 · 파일 81개 · 실패 0):
  **2018~2025 여덟 해 모두** 취득원가 표의 행이 `Banks, insurance and finance /
  Consumer products / Commercial, industrial and other` 셋뿐이다. 옛 공시에도
  **종목별 취득원가는 없다.** 서식 목록에 `ARS` 도 없다(다만 그때 상위 18개만
  찍어 확정은 아님 — 자르는 것은 이번에 고쳤다).
- 굳힘: **여기서 멈춘다.** 미리 정해 둔 멈출 자리이고, 화면의 추정 매수가는
  **추정으로 둔다.** *"연차보고서로 우리 계산을 검증한다"* 를 다시 계획에 넣지 말 것.
  대신 **종목별 시가는 해마다 적힌다**("상위 5개 … Apple Inc. – $73.7 billion").
  그것으로 우리 13F 값을 대조했다 — 5개 연말 × 5종목 25칸, **2023년은 반올림까지
  일치**, 나머지는 최대 6.5%이고 **어긋남이 한 방향**(우리가 늘 같거나 작음).
  가설은 자회사가 따로 내는 13F 이지만 **확인한 사실이 아니다.**
  전체 취득원가 총액 8년치도 로그에 있다(2018 102,867 … 2025 85,389 백만$).
- 넘김: "정기 검사 + 알림"은 **대상이 바뀌었다** — 매수가가 아니라 **보유 금액**을
  해마다 XBRL 로 대조하는 것. 만들지 말지는 사용자 판단. 한 방향 어긋남의 원인도
  안 밝혀졌다. 토요일(09-26) `splitsFrom` 확인은 그대로 남아 있다.

## 2026-09-23 · Claude · PR #83
연차보고서에 **종목별 취득원가가 없다** — 정찰 2차의 답. 3차로 옛 10-K·주주 서한을 본다
- 파일: scripts/probe_annual.py · .github/workflows/probe-annual.yml ·
  CLAUDE.md · 이 일지
- 규칙(실측, run 35882366178 · 23파일 전부 받음): 취득원가 표
  `Investments in equity securities (Detail)` 의 **행은 업종이다** —
  `us-gaap_EquitySecuritiesByIndustryAxis` · `Banks, insurance and finance
  [Member]`. 10-K(R69)도 10-Q(R59)도 같다. 종목 이름은 **묶음으로만** 나오고
  (`brka_Alphabet…AndCocaColaCompanyMember`) 그 묶음에 붙는 값은 취득원가가
  아니라 **시가 비중**(상위 5개 66%)이다 — 13F 로 이미 아는 값이라 검증이 안 된다.
- 굳힘: **이 저장소의 전제 하나가 틀렸다.** *"버크셔는 연차보고서로 우리 계산을
  검증할 수 있어서 첫 번째로 골랐다"* 는 지금 공시 기준으로 사실이 아니다.
  CLAUDE.md 세 곳에 정정을 달았다(1274·1352행·9-3). **다시 그 전제로 계획을
  세우지 말 것.** 범위 차이도 크다 — 10-K 의 equity securities 에는 지분법
  (크래프트하인츠·옥시덴탈)이 빠지고 13F 에 없는 일본 상사가 들어 있다.
  XBRL 태그라는 점은 그대로 사실이다(읽을 것만 있으면 자동 대조는 튼튼하다).
- 넘김: **3차 정찰을 눌러야 한다** — 10-K 여덟 해를 `--light` 로(10MB 본문 건너뜀)
  훑어 옛 공시에 종목별 취득원가가 있었는지 보고, 제출 목록의 서식 census 로
  **주주 서한(ARS)** 유무를 공짜로 확인한다. **둘 다 빈손이면 거기서 멈추고**
  *"연차보고서로 종목별 대조는 불가능"* 을 적고 추정을 추정으로 둔다.
  토요일(09-26) `splitsFrom` 확인도 남아 있다.

## 2026-09-23 · Claude · PR #82
연차보고서 정찰 1차 결과 반영 — XBRL 태그는 확인, 표는 내가 로그를 잘라 놓쳤다
- 파일: scripts/probe_annual.py · .github/workflows/probe-annual.yml ·
  CLAUDE.md · 이 일지
- 규칙(실측, run 35881516841): **연차보고서 취득원가는 XBRL 로 태그돼 있다** —
  `FilingSummary.xml` 에 낱장 146개, 그중 `Investments in equity securities`
  (10-K R15 · 10-Q R14). **10-Q 에도 같은 주석이 있다** → 분기마다 잴 수 있을
  공산이 크다(안의 표는 아직 못 봄). 본문은 10-K 10.4MB · 표 120개.
- 굳힘(내가 만든 함정 셋, 전부 고침): ① **버크셔 표는 칸 사이에 빈 칸을 잔뜩
  끼운다** — 줄이 400자를 넘어 통째로 빠졌다. 이어지는 칸 경계를 하나로 뭉개고
  제한을 1,200자로. ② **이름 목록을 잘라 찍지 말 것** — 27개 중 12개만 찍어
  `(Details)` 낱장이 목록에서 사라졌다. ③ **`Cybersecurity` 가 `securit` 에
  걸린다** — 받아 볼 여섯 칸 중 한 칸을 잡아먹었다. 그리고 **낱장은 앞머리만
  찍으면 주석 설명 문단에서 끝난다** — 보유 종목 이름이 걸린 줄을 따로 모은다.
  칸 경계 문자는 **이스케이프가 아니라 실제 글자로** 넣었다(8번의 `\25B8`).
- 넘김: **사용자가 Probe Annual 을 한 번 더 눌러야** A(표가 어디 있나)와
  D(애플이 실리나)의 답이 나온다. 그 로그를 보고 대조 코드·주기·경고/오류
  문턱을 정한다. 토요일(09-26) 첫 전체 재수집의 `splitsFrom` 확인도 남아 있다.

## 2026-09-23 · Claude · PR #81
연차보고서 취득원가 정찰 — 추정 매수가를 바깥 자료와 처음 맞춰 보려는 준비
- 파일: scripts/probe_annual.py · .github/workflows/probe-annual.yml ·
  CLAUDE.md · 이 일지
- 규칙: **정찰은 파서가 아니다.** 받아서 재고 원본을 남길 뿐이고, 걸린 줄은
  숫자를 뽑지 않고 **통째로** 찍는다(열·단위·연도는 사람이 봐야 한다).
  XBRL 태그 여부는 `FilingSummary.xml` 의 낱장 목록으로 본다 — 태그 이름을
  짐작해 `companyconcept` 를 찌르지 않는다. 찾을 종목 이름은 **자료에서**
  뽑는다(최신 분기 보유의 첫 낱말). **"찾는 표가 없더라"는 빨간불이 아니다** —
  하나도 못 받았을 때만 실패. 아티팩트를 개발 환경에서 못 받으므로 **핵심은
  로그에도 찍는다**(probe_sec.py 와 같은 이유).
- 굳힘: 대조 대상은 **애플**이 최적이다(2016년부터 사서 전 구간이 우리 자료
  안). 아멕스·코카콜라는 1998년 이전 매수라 **대조 자체가 안 된다** —
  `집계 전부터 보유` 로 비워 두는 그 자리다. stockcircle 과 0.1% 맞은 것은
  **검증이 아니다**(저쪽도 같은 방법). 알림은 **새로 만들지 않는다** —
  워크플로 실패 → notify.py → 텔레그램이 이미 있다.
- 넘김: **사용자가 Actions → Probe Annual 을 눌러야** 다음이 있다. 그 로그를
  보고 (가) 대조 코드 (나) 주기 (다) 경고/오류 문턱을 정한다. 정기 검사와
  텔레그램 알림은 **그 뒤**다 — 무엇을 읽는지 모르는 채로 예약을 만들 수 없다.
  토요일(09-26) 첫 전체 재수집에서 `splitsFrom` 확인도 아직 남아 있다.

## 2026-09-23 · Claude · PR #80
팔린 종목을 방문자 파일에 안 쌓는다 (사용자 판단) · 평가 금액 칸의 뜻을 문서에 남김
- 파일: scripts/fetch_prices.py · scripts/tests/test_prices.py · CLAUDE.md · 이 일지
- 규칙: `prices.json` 에는 **이번 분기 보유만** 남긴다(`series = dict(saved)` →
  `{c: saved[c] for c in required if c in saved}`). 화면이 읽는 것이 그것뿐이고,
  그대로 두면 버크셔만 18MB·8명이면 73MB 가 된다(실측). 버리는 값은 **재진입 때
  한 번 다시 받는 것**뿐이다 — 28년에 37번, 요청 1번·74KB, 게다가 새 종목이
  들어올 때와 **같은 길**이라 분할·분사도 그 한 번에 따라온다.
  **창고를 봇 전용 파일로 가르지 않았다** — 두 벌이 되면 갈라진다.
  `main()` 에 **공시책이 하나도 없으면 멈추는 가드** — 없으면 위 규칙이 파일을
  통째로 비운다.
- 굳힘: 실패한 종목은 옛 값을 그대로 지킨다(버리는 것은 *목록에 없는* 종목뿐).
  **검사가 `main()` 을 부를 때는 `OUT` 을 임시 폴더로 갈아끼운다** — 가드를
  되돌려 확인하다가 **저장소의 `prices.json` 을 실제로 비웠다**(화면 44건 중
  7건이 무너져서 알았고 `git checkout` 으로 되돌림).
  분기별 보유 변화 표의 `평가 금액` 은 **곱이 맞는 쪽**(보유×가격)으로 둔다 —
  EDGAR 와 4.4% 어긋나는 줄은 **제퍼리스 진입 1줄**뿐이다(전에 적어 둔
  `레나B 9분기 4.6~5.2%` 는 틀린 값이라 재서 고쳤다).
- 넘김: 토요일(09-26) 첫 전체 재수집에서 `prices.json` 에 `splitsFrom` 이 붙고
  옛 분할이 실리는지 확인할 것. 버크셔 연차보고서로 추정 매수가 대조는 아직.
  검사 3건 추가(파이썬 57 · 화면 44), 되돌려 2/2 잡힘.

## 2026-09-23 · Claude · PR #79
분할 원칙 — 깊이는 공시가 정하고, 가격은 사건 전부를 따른다 (사용자가 원칙 지정)
- 파일: scripts/fetch_prices.py · titans/shared/investor.js · 검사 아홉 · CLAUDE.md · 이 일지
- 규칙: 깊이 = **그 종목이 처음 공시에 나온 분기**(15년 창보다 늦게 잡지 않음).
  화면은 붙어 있는 두 공시 사이만 묻는다. 더 옛날 투자자가 들어오면 `splitsFrom`
  비교로 **저절로 다시 판다**. **야후 `splits` 는 "종가를 이만큼 나눠 놨다"는
  기록**이라 13F 값에 같은 것을 적용하면 두 자료가 같은 자가 된다(465분기 전부
  일치). 책을 둘로: `days`=진짜 분할(주식수+가격) · `adj`=모든 사건(가격만).
  **평균단가는 `fs/fp` 배** — 인적분할은 주식수가 안 변해 원가만 내려간다.
- 굳힘: 26줄 중 움직인 것은 **제퍼리스 하나**(평균단가 29.50→28.20 · +69.4→+77.2%),
  주식수·증감은 전부 그대로. 레나는 A·B 배수가 달라 기존 규칙이 거른다.
  검사 9건 추가(화면 44 · 파이썬 54), **되돌려 7/7 잡힘**(처음엔 셋이 안 잡혀
  검사를 세 개 더 만듦).
- 넘김: **`prices.json` 은 방문자가 받는 파일인데 팔린 종목이 쌓인다** —
  지금 2.2MB, 버크셔 전체 18MB, 8명이면 73MB(실측). 창고를 가르든 버리든
  정해야 한다. 사용자가 "보관"으로 정한 자리라 숫자만 알리고 안 건드렸다.
  분기별 보유 변화 표의 `평가 금액` 은 인적분할 9분기에서 공시와 4.6~5.2% 어긋난다.

---

## 2026-09-23 · Claude · PR #79
분할 기록을 상장 때까지 넓힘 — 정찰의 빨간불이 답이었다 (사용자가 정찰 실행)
- 파일: scripts/fetch_prices.py · titans/shared/investor.js ·
  scripts/probe_splits.py · 검사 넷 · CLAUDE.md · 이 일지
- 규칙: **월봉으로 싸게 받지 않는다** — AXP 1983-02-11 4:3 이 월봉 응답에만
  빠져 있었다. 일봉으로 받고 **창 밖 옛 바는 버린다**(`DEEP=1970-01-01`,
  저장은 15년 그대로라 파일이 안 커진다). 덮인 구간의 기준은 가격 시작일이
  아니라 **분할을 훑은 날**(`splitsFrom`) — 표식 없는 옛 파일은 예전 그대로다.
  **옛 바까지 세면 반쪽 응답 그물이 헐거워진다**(내가 연 구멍, 검사로 닫음).
  답이 나온 질문은 더 이상 빨간불이 아니다 — 정찰은 **못 받았을 때만** 실패.
- 규칙(사용자 지적 — "로드가 세게 걸리는 거 아냐?"): **상장 때부터는 종목마다
  한 번만 훑는다.** 요청 수는 29번 그대로이고 받는 양만 10.8→33MB 인데, 옛
  분할은 변하지 않으므로 매주 다시 받는 것은 낭비다. 이미 훑은 종목은 15년
  창만 받고 **창 밖 분할은 책에서 되살린다**(안 하면 그 주에 지워진다).
  티커가 바뀌면 표식을 물려받지 않는다.
- 굳힘: 스핀오프가 새 자료에서도 섞여 왔고(AXP 1994·2005 — **2005 는 공시
  구간 안**) 기약분수 거름망이 다섯 건 전부 버렸다. 봇이 돈 뒤의 파일을
  흉내 내어 26종목을 재니 **변화 0건**(애플 +631% 그대로). 검사 6건 추가
  (화면 40 · 파이썬 51), **되돌려 6/6 잡힘**.
- 넘김: **머지돼도 봇이 한 번 돌기 전까지 화면은 안 바뀐다.** 토요일 전체
  재수집에서 `prices.json` 에 `splitsFrom` 이 붙는지 확인할 것. 야후는
  개발 환경에서 막혀 있어 수집기는 흉내 응답으로만 쟀다.

---

## 2026-09-23 · Claude · PR #78
분할을 추측 대신 진짜 기록으로 — 야후 splits 는 분할 목록이 아니었다 (사용자 지적)
- 파일: titans/shared/investor.js · scripts/probe_splits.py ·
  .github/workflows/probe-splits.yml · 검사 · CLAUDE.md · 이 일지
- 규칙: **없는 것을 만들기 전에 저장소부터 뒤진다** — `prices.json` 에 진짜 분할이
  이미 들어 있었고 화면이 안 읽고 있었을 뿐이다. **야후 `splits` 는 '주가를
  보정해야 하는 사건' 목록이라 스핀오프가 섞여 있다**(제퍼리스 2023-01-17
  `1046:1000` — 주식수는 433,558주 그대로). **기약분수로 줄여 작은 정수만 받는다.**
  **모르는 구간은 1 이 아니라 `undefined`** 로 답해 추측기로 넘긴다.
- 굳힘: 저장된 21건 중 9건만 받고 12건 버림. 역분할(1:10)도 이제 잡힌다.
  26종목 결과는 추측 경로와 **글자까지 같음**. 검사 3건 추가(39건),
  되살려 3/3 잡힘. 커버 시작일 초기값을 `"9999"` 로 둬서 **기능이 안 켜지던
  버그**를 스스로 냈다 — 새 길로 갔을 때 값이 달라지는 것을 실제로 봐야 한다.
- 넘김: **2011-09 이전은 아직 추측이다**(아멕스 3:1 2000 · 무디스 2:1 2005).
  닫으려면 수집기 창을 넓혀야 하는데 야후가 개발 환경에서 막혀 있다.
  **사용자가 Actions → Probe Splits 를 한 번 눌러야** 다음이 열린다.

---

## 2026-09-23 · Claude · PR #78
Codex 검수 P1·P2 셋 — 3:2 분할 오판 · 반쪽 실행 초록불 · 빠진 분기 (사용자 요청)
- 파일: titans/shared/investor.js · investor.css · scripts/fetch_13f.py ·
  검사 셋 · CLAUDE.md · 이 일지
- 규칙: **2배 미만 분할은 주식수가 정확히 맞을 때만 인정한다.** 사람의 매매는
  1.500000 에 안 떨어진다. **`5:4`·`4:3` 은 13F 만으로 못 잡는다** — 넣으면
  12건이 오탐이다. 못 잡는 쪽이 낫다: 안 잡으면 막대로 보이고 틀린 배수로
  고치면 안 보인다. **반쪽 실행은 받은 것을 저장한 뒤 빨간불로 끝낸다.**
- 굳힘: 28년 3,741쌍 중 6건만 달라지고 지금 26종목은 불변(애플 +631% 그대로).
  `qGap()` 이 빠진 분기를 세고 머리글·안내 줄이 같이 바뀐다. 검사 5건 추가
  (화면 36 · 파이썬 46), **되살려 5/5 잡히는 것 확인** — 종료코드 검사는
  처음에 옛 가드에 걸려 거짓 통과했고 다시 짜서 잡았다.
- 넘김: Codex 검수 나머지 여섯(옵션 합산 P1 · 보조 수집 복구 P2 · 옛 공시
  반복 P2 · 단위 경계 P2 · CRLF P3 · 문서 드리프트 P3)은 미착수.
  **수집기는 개발 환경에서 SEC 가 막혀 흉내로만 검증했다 — 머지 뒤 첫 실행이
  진짜 확인이다.**

---

## 2026-09-23 · Claude · PR #78
한국어·영어 표현 손질 11건 + 죽은 사전 키 6개 정리 (사용자 요청 — Codex 검수와 병행)
- 파일: titans/shared/investor.js · scripts/tests/titans.test.cjs · CLAUDE.md · 이 일지
- 규칙: **검수는 사전이 아니라 화면에 찍히는 글자로 한다.** 사전에만 있고
  화면에 없는 문장을 검수 목록에 올렸다가 `grep` 해 보고서야 죽은 키인 걸 알았다.
  **한 사건에 두 이름을 주지 않는다** — 계기판은 `EXITED`, 사건 줄은 `Sold out`
  이었다. **한글은 고정폭에서도 두 칸**이라 이름표 폭을 글자 수로 재면 안 된다.
- 굳힘: 영어 단수(`1 quarters`) · `held` 세 뜻 · `Filing` 열에 분기말 날짜 ·
  차트와 표의 숫자 표기 불일치(사용자 결정 — 차트를 표에 맞춤) · 한국어
  `주식 수` 띄어쓰기. 검사 4건 추가(32건), **되살려 4/4 잡히는 것 확인**.
  사전 열쇠 37개가 전부 쓰이는지, 두 언어 열쇠가 같은지를 검사가 막는다.
- 넘김: 눈썹줄 `Titans' picks` 는 손대지 않았다(브랜드 · 사용자 판단).
  Codex 검수 결과 교차확인은 별도 보고 — P1 셋 중 **분할 3:2 오판이 제일 급하다**.

---

## 2026-09-23 · Claude · (이 PR)
Codex 검수에 넘기기 전 — 낡은 지도 셋을 고침 (사용자 요청)
- 파일: 다음에 할 일.md · CLAUDE.md(구조 트리) · AGENTS.md · 이 일지
- 규칙: **`다음에 할 일.md` 에는 사용자가 직접 할 일만 적는다.** 끝난 일·정해진
  것을 여기 한 벌 더 두면 갈라진다 — 실제로 9일 동안 "대가들의 선택은 아직
  시작 안 함"이라고 적고 있었다. 나머지는 CLAUDE.md 를 가리킨다.
  **AGENTS.md 의 "상대에게 검수를 요청하지 않는다"는 어시스턴트끼리의 규칙이다** —
  주인이 검수를 요청하면 그대로 하되, 고치기 전에 목록으로 먼저 보고한다.
- 굳힘: CLAUDE.md 구조 트리에 **검사 파일 5개가 통째로 빠져 있었다**(+ 워크플로 2 ·
  probe_amendments.py · portrait.webp · .gitignore · __init__.py). 트리는 검수자가
  "뭘 돌려 봐야 하나"를 찾는 자리다. 지금 빠진 파일 0건(스크립트로 대조).
  `data` 브랜치는 사용자가 이미 지웠다 — 문서만 남아 있었다.
- 넘김: 머지된 브랜치 11개가 남아 `backup/` 둘이 묻혀 있다(사용자 몫).
  Search Console 색인 판정 대기 — 그 결과로 SEO 방향이 갈린다.
  두 번째 투자자 · 연차보고서 대조 · 영어 `--up` 대비 4.49 미착수.

---

## 2026-09-23 · Claude · (이 PR)
소개 글의 한글 오타 `횝내` → `흉내` (사용자가 잡음)
- 파일: titans/berkshire/index.html · CLAUDE.md · 이 일지
- 규칙: **파이썬으로 한글을 써 넣을 때 유니코드 이스케이프를 쓰지 않는다.**
  `\ud69d`(횝)를 `\ud749`(흉)로 잘못 적었다. 제어문자가 아니라 멀쩡한 한글
  한 글자라 기존 제어문자 검사에 안 걸린다 — 이스케이프로 적으면 쓴 사람도
  읽을 수 없다. 저장소 전체를 훑어 같은 글자는 이 한 건뿐이었다.
- 굳힘: 같은 줄의 인용 띄어쓰기도 고침 — `'영원히' 입니다` → `'영원히'입니다`.
- 넘김: 앞 항목의 넘김 줄 그대로.

---

## 2026-09-22 · Claude · (이 PR)
투자자 소개에 캐리커처를 넣고 그림 상자를 3:2 로 (사용자가 그림을 만들어 옴)
- 파일: titans/berkshire/portrait.webp(새 그림) · index.html ·
  titans/shared/investor.css · docs/design-system.md · CLAUDE.md · 이 일지
- 규칙: **그림 색이 맞는지는 `L*a*b*` 로 잰다.** 첫 후보는 바탕이 크림색이라
  노랑↔파랑 축에서 혼자 `b* +18.5`(카드 0 · 종이 −2.3), 카드와 ΔE 20.2 였다.
  밝기는 같아서 "누런 종이"로 보이는 것이지 어두운 것이 아니다.
  **바탕이 카드와 같은 순백이면 테두리를 두르지 않는다** — 테두리만 네모로 떠서
  없는 상자를 그린 꼴이 된다. **상자 비율은 잉크 범위로 정한다**: 1024×559 지만
  흰 여백을 빼면 733×541(≈3:2)이라, 1:1 상자에 넣으면 `cover` 가 엄지를 통째로
  자른다.
- 굳힘: 잘라 넣어도 이음매가 안 보이는 이유는 바탕이 카드와 같은 흰색이기 때문.
  좌우 51·52px 여백을 남겨 잘린 것 0.
- 넘김: **그림이 엄지를 세운 구도**다 — 추천 몸짓이고 바로 아래가 보유 목록이라
  `사라`로 읽힐 수 있다. 알렸고 사용자가 그대로 가기로 했다. 바꾸려면
  `portrait.webp` 한 장만 갈면 된다. SEO 분석 · 영어 `--up` 대비 4.49(비중
  막대 위) 미착수. 정정 병합은 2026-09-20 실행에서 7분기·43분기로 확인 끝.

---

## 2026-09-22 · Claude
머리글 아래에 투자자 소개 — 왼쪽 그림 · 오른쪽 글과 명언 둘 (사용자 요청)
- 파일: titans/berkshire/index.html · titans/shared/investor.css · investor.js ·
  scripts/tests/titans.test.cjs · docs/design-system.md · CLAUDE.md · 이 일지
- 규칙: **소개 글은 투자자의 HTML 에 글자로 박는다.** 사전(`D`)에 넣으면 JS 가
  그리게 되고 크롤러가 받는 페이지에서 사라진다(본 사이트 `.about` 과 같은 자리).
  두 언어를 다 넣고 CSS 가 한쪽만 보인다. 공통 JS 는 이 덩어리를 **들어냈다가**
  머리글 아래 도로 넣을 뿐 내용을 모른다. 인용은 `<cite>` 출처 없이 싣지 않는다.
- 굳힘: 감춰진 형제 때문에 `*+*` 여백은 첫 줄에도 붙는다 → `gap` 을 쓴다.
  작은 고정폭에 한글을 넣으면 자간이 벌어진다 → 출처 줄은 `--cond`.
  그림이 없으면 `.nofigure` 가 그림 칸을 통째로 뺀다(깨진 그림 0).
- 넘김: **그림 파일이 아직 없다** — `titans/berkshire/portrait.png` 에 1:1
  (1024×1024)로 넣으면 그 자리에 나온다. 사용자가 다른 AI 로 만들어 온다.
  정정 병합(PR #64)은 2026-09-20 일요일 실행에서 **7분기 반영 · 43분기
  `pre-xml` 표시**로 예행값과 일치했다(확인 끝). SEO 분석 · 영어 `--up`
  대비 4.49(비중 막대 위)가 미착수.

---

## 2026-09-22 · Claude
사건 줄(재진입·전량매도)에 로고·섹터 · 사건 블록을 한 격자로 (사용자 요청)
- 파일: titans/shared/investor.js · investor.css · scripts/tests/titans.test.cjs ·
  CLAUDE.md · docs/worklog/claude.md
- 규칙: 사건 줄은 목록이 쓰는 `markHTML()`·`sectorOf()` 를 **그대로** 쓴다.
  **격자는 줄이 아니라 `.events` 블록이 쥔다**(`.ev{display:contents}`) —
  줄마다 두면 이름표 폭이 달라 마크가 줄마다 다른 자리에서 시작한다.
  `display:contents` 요소는 상자가 없다: 여백은 부모 `row-gap`, 글꼴은 자식이
  직접, **검수에서 `getBoundingClientRect()` 는 자식을 재야 한다.**
- 굳힘: 전량매도 줄도 마크·섹터가 나온다(`B.out` 이 cusip·key 를 들고 있다).
  못 찾으면 글자 타일 + 빈 섹터 — 틀린 것을 적지 않는다.
- 넘김: 정정 병합(PR #64)의 실제 SEC 실행은 아직 0회 — 일요일 01:00 UTC 전체
  점검이 첫 실행. SEO 분석 · 영어 `--up` 대비 4.49(비중 막대 위)가 미착수.
