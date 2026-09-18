# ChatGPT(Codex) 일지

형식과 규칙은 `README.md`. **맨 위가 최신이다.** Codex 만 이 파일에 쓴다.

## 2026-09-19 · Codex · PR #55
일별 종가 15년치 공유 캐시·장 종료 후 자동 갱신·매수 이전부터 이어지는 실제 주가선
- 파일: scripts/fetch_prices.py · data/titans/prices.json · update-prices.yml · check-titans.yml · scripts/tests/* · titans/berkshire/index.html · CLAUDE.md · design-system.md · 이 일지
- 규칙: 공급처·종류 구분·가격/공시 계산 분리·저장 안전성·검증은 CLAUDE.md 9-3-1의 일별 종가 저장·갱신·연결.
- 굳힘: 공급처 이름은 화면에 추가 안 함(사용자 결정). 가격 눈금선·차트 제목/부제/캡션·목록 스티커·삭제 기간 복구 금지.
- 넘김: 공개 접근을 재배포 허가로 보고하지 말 것. GitHub 예약은 머지 후 확인 필요. 여러 투자자 13F 수집·정정 병합은 별도 미완성.

## 2026-09-18 · Codex · PR #54
차트 막대 높이·분기 폭·상향 방향·점선 말풍선·이전 거래 카드와 중복 문구 정리
- 파일: titans/berkshire/index.html · scripts/tests/titans.test.cjs · CLAUDE.md · docs/design-system.md · 이 일지
- 규칙: 최종 디자인·가격 자료 상태·25건 검사와 브라우저 검증은 CLAUDE.md 9-3-1의 차트 디자인 후속.
- 굳힘: 양방향 막대 모두 위로, 최대 34.5/27px. 삭제한 차트 제목·부제·아래 캡션과 기존 금지 항목 복구 금지.
- 넘김: 일별 종가 미연결. 사용자는 현재 무료만. 공개 표시 허용 공급처 확인·출처 표시·종류별 가격·자동 수집 후 선택 설정 활성화.

## 2026-09-18 · Codex · PR #53
공시 기준 표현·모바일 숫자 안내·최대 매도·작은 비중·정적 소개와 자동 검사
- 파일: titans/berkshire/index.html · scripts/tests/titans.test.cjs · .github/workflows/check-titans.yml · CLAUDE.md · docs/design-system.md · 이 일지
- 규칙: 최종 목표·최종 동작·검증은 CLAUDE.md 9-3-1의 개선 권장 후속. 공통 틀과 새 분기 갱신을 모의 자료로 확인.
- 굳힘: 삭제했던 목록 스티커·기간·가격 눈금·보유 연차 자를 복구하지 않음. 실제 데이터와 기존 각주는 그대로.
- 넘김: 머지 대기. 여러 투자자의 수집 설정과 정정 자동 병합은 아직 미완성. SEC 실시간 수집은 이번에 검증 안 함.

## 2026-09-18 · Codex · PR #52
검수한 필수 오류 여섯 가지 수정 — 기록 보존·신규 표시·기간·전량매도·분할·변경일
- 파일: scripts/fetch_13f.py · titans/berkshire/index.html · .github/workflows/update-13f.yml · scripts/tests/* · CLAUDE.md · 이 일지
- 규칙: 원인·최종 동작·검증은 CLAUDE.md 9-3-1. PR #52는 2커밋, 회귀 검사 17건 통과.
- 굳힘: 과거 기록·가격 없는 매도를 보존. 눈금선·목록 스티커·삭제한 기간·보유 연차 자는 복구하지 않음.
- 넘김: 사용자 머지 대기. 정정 원문 병합·연차보고서 대조·각주·주별 시세는 보류 그대로, SEC 실시간 수집은 미검증.
