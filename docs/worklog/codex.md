# ChatGPT(Codex) 일지

형식과 규칙은 `README.md`. **맨 위가 최신이다.** Codex 만 이 파일에 쓴다.

## 2026-10-10 · Codex · (이 PR)
투자자 8명 최신 공시 요약을 한영 원본 HTML로 자동 게시
- 파일: titans/shared/overview.js·investor.* · 투자자 HTML ×8 · publish_titans_overviews.cjs · 워크플로·검사·사이트맵 · CLAUDE.md · design-system.md · 이 일지
- 규칙: 동일 생성기를 브라우저와 자동 게시에서 공유. 구성 차이는 매매로 단정하지 않음. 상세 동작·검증은 CLAUDE.md 6-2의 2026-10-10 항목.
- 굳힘: backup/v1.12 보관. PR #138 포함 main에서 진행. 기존 소개·주소·계산 유지. 새 투자자도 같은 생성기 사용.
- 넘김: 사용자 merge 후 자동 갱신 첫 실행·배포 원본 요약 확인. Google/네이버 재수집·검색 실적은 이후 확인하며 중복 색인 요청하지 말 것. Claude 일지의 ET 추적은 별도 미완료.

## 2026-10-08 · Codex · (이 PR)
검수 후속: 배당 자료 누락 거부·통계 문구 수정·사무엘 날짜 복구·올림픽 결과 설명과 모바일 배치
- 파일: timing/ · samuel/ · olympics/ · backtest.py · check_about.py · update-long/olympics.yml · 검사 · CLAUDE.md · design-system.md · 이 일지
- 규칙: 과거 빈도를 미래 확률로 쓰지 않음. 자동화는 ETF 성공 후 연결. 상세 근거·검증은 CLAUDE.md 8-1-1·9-3-2·9-3-3.
- 굳힘: backup/v1.11 보관. 기존 계산·매매 규칙·인물별 소개·VIX 숨김·정적 본문 유지. 주식/BIL 손익은 당일까지의 실제 기록에서 계산.
- 넘김: 사용자 merge 뒤 새 자동화 연결의 첫 실제 실행 확인. 기존 새 서비스 색인 확인은 남아 있으며 네이버 재수집 중복 요청 금지.

## 2026-10-07 · Codex · (이 PR)
투자 올림픽의 각 순위 카드에 투자 방식 요약을 한영으로 상시 표시
- 파일: olympics/app.js · style.css · index.html · CLAUDE.md · design-system.md · 이 일지
- 규칙: 적용된 조건만 설명에 반영. 동작·검증은 CLAUDE.md 9-3-3가 정본.
- 굳힘: 기존 계산·데이터·접힌 상세 이야기 유지. PC 숫자 줄 정렬·모바일 숫자 이름표 유지.
- 넘김: 사용자 화면 확인 및 merge. 앞 PR의 배포 후 한영 URL·색인 확인은 남아 있음.

## 2026-10-07 · Codex · PR #135
투자 올림픽: 같은 목돈의 다섯 전략을 실제 공개 기록으로 재생하는 네 번째 서비스
- 파일: olympics/ · scripts/olympics/ · fetch_olympics.py · data/olympics/ · 대문·사이트맵·CI·검사 · CLAUDE.md · design-system.md · 이 일지
- 규칙: 사용자 승인 알리시아 예산·비례 매도, 전략 모듈·당시 공개 공시·배당 반영 가격. 계산·범위·실측·한계는 CLAUDE.md 9-3-3가 정본.
- 굳힘: 변경 전 backup/v1.10. 없는 가격·미래 신호를 만들지 않음. 한영·텔레그램 실패 경로·원래 세 서비스 유지.
- 넘김: 사용자 화면 확인 및 merge, 배포 후 /olympics/ 한영 실제 URL·색인 확인. 더 오래된 올림픽 기록은 상장폐지·당시 공개 자료·기업 행동 확인 후 확장. 기존 네이버 재수집 중복 요청하지 말 것.

## 2026-10-06 · Codex · PR #134
사무엘의 결정: 같은 목돈의 일시금·분할 투자 비교를 세 번째 서비스로 추가
- 파일: samuel/ · data/samuel/ · samuel_data.py · fetch_long.py · 대문·사이트맵·CI·검사 · CLAUDE.md · design-system.md · 이 일지
- 규칙: 같은 초기 원금·대기 BIL 포함·실제 전체 일봉·완료 기간만. 사용자가 연이율 입력 대신 BIL 선택; 구현·자료·검증은 CLAUDE.md 9-3-2가 정본.
- 굳힘: 변경 전 backup/v1.9 보관. 한영·기존 서비스·자동 수집·텔레그램 실패 경로 유지. 미래 확률이나 추천으로 표시하지 않음.
- 넘김: 사용자 화면 확인 및 merge. 배포 후 새 /samuel/ 한영 실제 URL·색인 확인. 네이버 기존 주요 한국어 4주소는 10-05 재수집(200·색인 허용·새 제목 확인), 색인은 아직 안 됨; 중복 요청하지 말 것.

## 2026-10-05 · Codex · (이 PR)
12화면의 언어 스위치를 국기·언어 이름 드롭다운으로 통일
- 파일: shared/language-picker.* · assets/language/* · index.html · timing/index.html · titans/ · 기존 검사 경계·CI · CLAUDE.md · design-system.md · 이 일지
- 규칙: 구현·새 언어 추가·검증은 CLAUDE.md 6번의 드롭다운 항목이 정본.
- 굳힘: 기존 주소·우선순위·저장값·언어별 차트색·계산·정적 본문 유지. 투자자 8명 모두 같은 부품.
- 넘김: 사용자 디자인 확인 및 merge. 네이버 주요 한국어 4주소 수집 요청은 10-05 접수; 재수집 후 제목·설명·색인 확인이 남음.

## 2026-10-05 · Codex · (이 PR)
전체 화면의 한영 대표 주소·공유 주소·언어 전환과 사이트맵 일치
- 파일: index.html · timing/index.html · titans/ 페이지·공통 JS · sitemap.xml · SEO 검사·CI · CLAUDE.md · design-system.md · 이 일지
- 규칙: 현재 한영 검색 주소 규칙과 검증은 CLAUDE.md 6-2의 2026-10-05 항목이 정본.
- 굳힘: 기존 ?lang= 주소 유지. 정적 한영 본문·디자인·계산·데이터 수집 유지. 기본 주소도 사이트맵에 유지.
- 넘김: 사용자 merge 후 사이트맵 재제출·Google 실제 URL 테스트. 앞서 대문/타이밍/목록 한국어 3개와 투자자 기본 주소 8개 색인 요청은 수락됨; 투자자 8명은 기존 색인 상태였고 Baupost 한국어 실시간 렌더링도 통과했음.

## 2026-10-05 · Codex · (이 PR)
거장 목록 상단 마지막 문장을 미국 상장 주식 안내로 변경
- 파일: titans/index.html · CLAUDE.md · 이 일지
- 규칙: 목록 소개의 현재 문구는 CLAUDE.md 9-3의 사용자 요청 항목이 정본.
- 굳힘: 지정한 마지막 문장만 한영 교체. 앞 소개·공통 면책·13F 안내 유지.
- 넘김: 사용자 merge.

## 2026-10-04 · Codex · (이 PR)
사용자 확정 대문·카드·다니엘 서사와 직접적인 검색 제목
- 파일: index.html · timing/index.html · titans/index.html · shared/investor.js · 투자자 index.html ×8 · CLAUDE.md · design-system.md · 이 일지
- 규칙: 문구·검색 제목·카드 정렬·검증은 CLAUDE.md 1번의 대문 문구·서사·검색 제목 확정 항목이 정본.
- 굳힘: 사용자 서사 유지. 거장 카드 마지막은 분기별 보유 변화로 명확화. 담백한 다니엘 상단·기존 계산 유지.
- 넘김: 사용자 merge. 나머지 페이지 문구 확정 후 색인 요청 및 SEO 정비.

## 2026-10-04 · Codex · (이 PR)
모든 투자자 모바일 보유 현황에 항목별 이름표와 고정 숫자 배치
- 파일: titans/shared/investor.css·js · 투자자 index.html ×8(캐시 표식) · titans.test.cjs · CLAUDE.md · design-system.md · 이 일지
- 규칙: 사용자 승인 시안 적용. 구현·검증은 CLAUDE.md 9-3-1의 2026-10-04 항목이 정본. 변경 전 backup/v1.8 보관.
- 굳힘: 공통 틀에서만 변경. PC 열 배치·차트·계산·수집·기존 유의사항 유지. 모바일의 옛 숫자 순서 안내는 항목별 이름표로 대체.
- 넘김: 사용자 merge. 별도 자료 수집·수동 배포 없음.

## 2026-10-03 · Codex · (이 PR)
대문 상단에 서비스 바로가기 메뉴
- 파일: index.html · CLAUDE.md · docs/design-system.md · 이 일지
- 규칙: 메뉴·확장·검증은 CLAUDE.md 1번의 상단 서비스 메뉴가 정본.
- 굳힘: 서비스 카드·스토리 유지. 확인되지 않은 실시간 표시나 상태 배지 없음.
- 넘김: 사용자 디자인 확인 및 merge. 별도 자료 수집·수동 배포 없음.

## 2026-10-03 · Codex · (이 PR)
다니엘의 두 차트 — 모바일 폭·조작부·선과 배경 정리
- 파일: timing/index.html · CLAUDE.md · docs/design-system.md · 이 일지
- 규칙: 변경 전 backup/v1.7 보관. 구현·검증은 CLAUDE.md 4번의 두 차트 디자인 조정이 정본.
- 굳힘: 담백한 상단 서사·기존 통계·낙폭 표시·기간 연동·VIX 숨김 유지. 기간 버튼 자체는 한 줄.
- 넘김: 사용자 디자인 확인 및 merge. 별도 자료 수집·수동 배포 없음.

## 2026-10-03 · Codex · PR #126
다니엘 화면을 대문과 잇는 디자인·담백한 상단 서사
- 파일: timing/index.html · scripts/tests/home.test.cjs · CLAUDE.md · design-system.md · 이 일지
- 규칙: PR #120~#125 확인 및 backup/v1.6 확보. 디자인·서사·검증은 CLAUDE.md 1번이 정본.
- 굳힘: 대문의 카드 전체 링크 유지. 다니엘 서사는 상단 정적 한영 본문. 푸른 상단 카드·큰 질문·번호 장식 복구 금지. 차트·계산·VIX 숨김·기존 면책 유지.
- 넘김: 사용자 디자인 확인 및 merge. 별도 수동 배포·자료 재수집 없음.

## 2026-09-30 · Codex · (이 PR)
승인한 이야기형 대문 — 접히는 서비스 카드와 새 캐리커처 단체사진
- 파일: index.html · assets/home/* · home/titans 검사 · check.yml · AGENTS.md · CLAUDE.md · design-system.md · 이 일지
- 규칙: 현재 디자인·자료 범위·검증은 CLAUDE.md 1번이 정본. 변경 전 backup/v1.2 확보.
- 굳힘: 번호 동등, 이야기는 처음에 접기. 큰 Q·신문형·준비 중 카드·버크셔 요약 복구 금지. 서비스는 계속 추가 가능.
- 넘김: 사용자 merge. 별도 데이터 수집·수동 배포 없음.

## 2026-09-29 · Codex · (이 PR)
PR #117 검수 후속 — 13F 안내 정확성·안내 페이지 왕복 언어 유지
- 파일: index.html · timing/index.html · titans/index.html · titans/13f/index.html · shared/investor.js · titans.test.cjs · CLAUDE.md · 이 일지
- 규칙: 가격 대조 범위·채권 예외·안내 링크의 언어 전달은 CLAUDE.md 9-3의 안내문 검수 후속이 정본.
- 굳힘: 수집·계산·전체 종목·공통 면책 문구 유지. 사이트에서 제외한 자료와 원래 공시에 없는 자료를 구분.
- 넘김: 사용자 merge. 별도 수동 배포·데이터 재수집 없음.
