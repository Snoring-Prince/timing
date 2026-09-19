# ChatGPT(Codex) 일지

형식과 규칙은 `README.md`. **맨 위가 최신이다.** Codex 만 이 파일에 쓴다.

## 2026-09-19 · Codex · PR #58
투자자 registry·SEC 통신·새 접수 감시·투자자별 원문 수집을 분리한 다중 13F 자동화
- 파일: data/titans/investors.json · scripts/titans/* · watch/fetch_13f.py · ticker/sector/price 수집기 · update/check workflow · tests · 관련 문서 · 이 일지
- 규칙: 평일 2회 최신 제출 목록만 확인하고 새 정규/정정 접수 때 해당 투자자만 전체 수집. 일요일·수동은 전체 확인.
- 굳힘: 모든 보조 수집기는 registry의 투자자 책을 읽음. 다른 CIK 자료 혼합 거부. 공시 오류와 티커·업종 오류는 구분해 텔레그램 알림.
- 검증: 모의 SEC/registry/분배·보존 22건, 화면 19건 통과. PR CI가 가격 포함 Python 33건 실행. 실제 SEC·Telegram은 머지 후 수동 실행에서 확인.
- 넘김: 정정 공시 수치 병합과 2013년 이전 텍스트 공시의 투자자 공통 변환은 미완성. 다음 투자자 추가 전 필요 여부 판단.

## 2026-09-19 · Codex · PR #57
모든 투자자의 디자인·화면·차트·계산을 한 벌의 공통 CSS·JS로 분리
- 파일: titans/shared/* · titans/berkshire/index.html · scripts/tests/titans.test.cjs · CLAUDE.md · design-system.md · 이 일지
- 규칙: 투자자별 파일에는 설정·고유 SEO·정적 영문 소개만 둔다. 공통 화면 구조와 디자인은 shared에서만 수정.
- 굳힘: 검색엔진용 정적 제목·설명·h1·소개는 각 URL에 유지. 기존 화면·계산·금지 디자인은 변경 안 함.
- 넘김: 여러 투자자 13F 수집 자동화·정정 병합은 미완성. 새 투자자 껍데기 자동 생성은 수집 구조 작업과 함께 검토.

## 2026-09-19 · Codex · PR #56
주가 수집·종목 식별·저장 실패를 기존 텔레그램 알림에 연결
- 파일: .github/workflows/update-prices.yml · CLAUDE.md · 이 일지
- 규칙: 실패 알림의 범위·순서·로그·오프라인 검증은 CLAUDE.md 9-3-1 주가 오류 텔레그램 알림 후속.
- 굳힘: 정상 실행/PR 검사에는 발송 안 함. 성공 자료 저장을 먼저 하고 기존 notify.py·Secrets 사용.
- 넘김: 실제 메시지 발송/수신은 이번에 확인 안 함. 예약 누락·알림 서비스 장애까지 감지하는 외부 감시는 없음.

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
