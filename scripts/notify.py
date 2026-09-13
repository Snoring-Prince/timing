#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""텔레그램으로 한 줄 알립니다. 워크플로가 실패했을 때 부릅니다.

왜 메일이 아니라 텔레그램인가
-----------------------------
GitHub 의 실패 메일은 계정 알림 설정에 걸려 있고, 예약 워크플로의 경우
**cron 줄을 마지막으로 고친 사람**에게만 갑니다. 설정을 건드리거나 시간표를
누가 바꾸면 조용히 끊깁니다. 텔레그램은 그 사슬을 안 탑니다.

설정 (저장소 Settings → Secrets and variables → Actions)
--------------------------------------------------------
    TELEGRAM_TOKEN   BotFather 가 준 토큰 — **어느 봇이든 상관없습니다.**
                     여기 넣은 토큰의 봇이 말을 겁니다. 코드는 봇을 모릅니다.
    TELEGRAM_CHAT    받을 chat id. 1:1 대화면 내 텔레그램 사용자 번호이고,
                     **봇이 달라도 같은 번호**입니다(단, 새 봇에게는 말을
                     한 번 걸어 둬야 봇이 나에게 보낼 수 있습니다).

**둘 중 하나라도 없으면 조용히 넘어갑니다(종료코드 0).** 알림을 못 보내는 것이
워크플로를 실패시킬 이유는 아닙니다 — 이미 실패해서 불려 온 참이니까요.
같은 이유로 텔레그램이 죽어 있어도 실패로 만들지 않습니다.

    python scripts/notify.py --title "제목" --body-file out.txt
    python scripts/notify.py --test
"""
import argparse
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/sendMessage"
LIMIT = 3500          # 텔레그램은 4096자까지. 꼬리말 자리를 남겨 둔다.


def send(token: str, chat: str, text: str) -> bool:
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(API.format(token=token), data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # 텔레그램은 왜 거절했는지 본문에 적어 준다. 토큰은 절대 찍지 않는다.
        try:
            why = json.loads(e.read().decode()).get("description", "")
        except Exception:
            why = ""
        print(f"텔레그램이 거절했습니다 ({e.code}) {why}")
        if e.code == 400 and "chat not found" in why.lower():
            print("  → TELEGRAM_CHAT 이 틀렸거나, 봇에게 말을 한 번도 안 걸었습니다.")
            print("    텔레그램에서 봇을 찾아 아무 말이나 한 번 보낸 뒤 다시 해 보세요.")
        if e.code == 401:
            print("  → TELEGRAM_TOKEN 이 틀렸습니다. BotFather 에서 다시 받아 넣으세요.")
        return False
    except Exception as e:
        print(f"텔레그램에 못 닿았습니다: {e}")
        return False
    if not body.get("ok"):
        print(f"텔레그램이 ok 를 안 줬습니다: {body}")
        return False
    return True


def compose(title: str, body: str, run_url: str, project: str = "") -> str:
    """제목은 굵게, 본문은 고정폭 상자로. 휴대폰에서 표가 안 깨진다.

    앞에 프로젝트 이름을 붙인다 — 봇을 여러 개 굴리거나 한 봇이 여러 곳에서
    말하면, 휴대폰 알림 미리보기에 앞부분만 보여서 어느 것인지 알 수 없다."""
    body = body.rstrip()
    if len(body) > LIMIT:
        body = body[:LIMIT] + "\n… (줄임 — 전체는 Actions 에서)"
    head = f"[{project}] {title}" if project else title
    out = f"<b>{html.escape(head)}</b>"
    if body:
        out += f"\n<pre>{html.escape(body)}</pre>"
    if run_url:
        out += f'\n<a href="{html.escape(run_url, quote=True)}">실행 기록 보기</a>'
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="알림")
    ap.add_argument("--body-file", help="본문으로 쓸 파일 (없으면 표준입력)")
    ap.add_argument("--test", action="store_true", help="시험 발송")
    a = ap.parse_args()

    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT", "").strip()
    if not token or not chat:
        missing = " · ".join(n for n, v in
                             (("TELEGRAM_TOKEN", token), ("TELEGRAM_CHAT", chat)) if not v)
        print(f"텔레그램 설정이 없어 건너뜁니다 (없는 값: {missing})")
        print("  저장소 Settings → Secrets and variables → Actions 에 넣으면 켜집니다.")
        return 0

    if a.test:
        title = "텔레그램 알림 시험"
        body = ("이 메시지가 보이면 설정이 끝난 것입니다.\n\n"
                "앞으로 이런 때 여기로 알려 드립니다.\n"
                "  · 매일 데이터 받기가 실패했을 때\n"
                "  · 주 1회 장기 이력 받기가 실패했을 때\n"
                "  · 주 1회 설명 글의 숫자가 낡았을 때\n\n"
                "아무 말이 없으면 다 잘 돌고 있다는 뜻입니다.")
    else:
        title = a.title
        if a.body_file and os.path.exists(a.body_file):
            body = open(a.body_file, encoding="utf-8").read()
        else:
            body = "" if sys.stdin.isatty() else sys.stdin.read()

    run = ""
    srv, repo, rid = (os.environ.get(k, "") for k in
                      ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    if srv and repo and rid:
        run = f"{srv}/{repo}/actions/runs/{rid}"
    project = repo.split("/")[-1] if repo else ""

    ok = send(token, chat, compose(title, body, run, project))
    print("보냈습니다." if ok else "못 보냈습니다. (워크플로는 이것 때문에 실패시키지 않습니다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
