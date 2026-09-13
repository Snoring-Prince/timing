#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""설명 글(.about)에 박힌 숫자가 아직 맞는지 대조합니다.

왜 필요한가
-----------
`index.html` 의 `.about` 문단은 **HTML 에 직접 박혀 있어야 합니다.** 사전(D)으로
옮기면 JS 가 그리게 되고, JS 를 안 돌리는 크롤러가 받는 페이지는 다시 빈 페이지가
됩니다(CLAUDE.md 6-2). 그래서 글 속 숫자도 손으로 적혀 있는데, `backtest.json` 은
주 1회 다시 계산됩니다. **아무도 확인하지 않으면 글의 숫자만 조용히 낡습니다.**

두 가지를 봅니다
----------------
1. 숫자가 맞는가      — 적힌 값과 다시 계산한 값의 차이
2. 문장의 논지가 사는가 — "평균이 중앙값보다 훨씬 크다", "공포가 셀수록 승률이 높다"

숫자는 조금씩 늘 움직입니다(표본이 매주 늘어남). 그래서 자릿수가 하나 바뀌었다고
매주 실패하면 아무도 안 봅니다. **글이 틀려 보일 만큼 벌어졌을 때만** 실패합니다.

  경고  적힌 자릿수와 다름 — 알려만 주고 넘어감
  오류  글이 오해를 부를 만큼 벌어짐 / 논지가 깨짐 — 종료코드 1

한국어와 영어 문단이 서로 다른 숫자를 말하는 경우도 오류입니다(한쪽만 고친 것).

    python scripts/check_about.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"
BT = ROOT / "data" / "backtest.json"

OK, WARN, ERR = "✓", "경고", "오류"


# ── 글에서 숫자 꺼내기 ────────────────────────────────────────────────
def prose(html: str) -> dict:
    """.about 의 한국어·영어 문단을 태그 없는 한 줄로."""
    i = html.index('<section class="panel about">')
    about = html[i : html.index("</section>", i)]
    out = {}
    for lang in ("ko", "en"):
        m = re.search(r'<div class="prose" data-lang="%s">([\s\S]*?)\n    </div>' % lang, about)
        if not m:
            sys.exit(f"{ERR}: .about 의 {lang} 문단을 못 찾았습니다. 구조가 바뀌었나요?")
        t = re.sub(r"<[^>]+>", "", m.group(1))
        t = t.replace("&amp;", "&").replace("&nbsp;", " ")
        out[lang] = re.sub(r"\s+", " ", t).strip()
    return out


def grab(text: str, pattern: str, label: str, lang: str):
    """문단에서 숫자 하나를 꺼낸다. 못 찾으면 그 자리에서 멈춘다 —
    조용히 건너뛰면 검사가 통과한 것처럼 보인다."""
    m = re.search(pattern, text)
    if not m:
        sys.exit(f"{ERR}: {lang} 문단에서 '{label}' 을 못 찾았습니다.\n"
                 f"       글을 고쳤다면 이 스크립트의 정규식도 같이 고쳐 주세요.\n"
                 f"       찾던 것: {pattern}")
    return float(m.group(1).replace(",", ""))


# ── 대조 항목 ────────────────────────────────────────────────────────
def build(bt: dict) -> list:
    spx = bt["indices"]["spx"]["curve"]
    fng, vix = spx["fng"], spx["vix"]
    y = fng["h"]["1Y"]
    win = {a["key"]: a for a in bt["axes"]}

    # (이름, 한국어 정규식, 영어 정규식, 실제값, 오차허용, 소수자리)
    return [
        ("표본 일수(공포탐욕 0 근처·1년)",
         r"있던 ([\d,]+)일을 보면", r"Across the ([\d,]+) days when",
         y["n"][0], max(3, y["n"][0] * 0.02), 0),
        ("평균 수익률",
         r"평균 수익률은 \+([\d.]+)%", r"mean return was \+([\d.]+)%",
         y["avg"][0], 1.0, 2),
        ("중앙값",
         r"중앙값은 \+([\d.]+)%", r"the median \+([\d.]+)%",
         y["med"][0], 1.0, 2),
        ("평균을 줄인 말(27% 번다)",
         r"사면 (\d+)% 번다", r'make (\d+)%',
         round(y["avg"][0]), 1, 0),
        ("중앙값을 줄인 말(11% 아래)",
         r"절반이 (\d+)% 아래", r"came in under (\d+)%",
         int(y["med"][0]), 1, 0),
        ("승률(지수 5)",
         r"확률이 (\d+)% 인데", r"a positive return a year later (\d+)% of the time",
         y["win"][5], 3, 0),
        ("승률(지수 24)",
         r"24 는 (\d+)%", r"in the same bucket, it was (\d+)%",
         y["win"][24], 3, 0),
        ("창 크기(±N)",
         r"그 값 ±(\d+) 인 날들", r"within ±(\d+) of it",
         win["fng"]["window"], 0, 0),
        ("표본 문턱(N일)",
         r"표본이 (\d+)일도 안 되는", r"fewer than (\d+) days",
         bt["min_n"], 0, 0),
        ("공포탐욕 전체 일수",
         r"3일부터 ([\d,]+)일입니다", r"covers ([\d,]+) days from 3 January 2011",
         fng["days"], max(3, fng["days"] * 0.01), 0),
        ("VIX+SPY 전체 일수",
         r"29일부터 ([\d,]+)일이라", r"it covers ([\d,]+) days from 29 January 1993",
         vix["days"], max(3, vix["days"] * 0.01), 0),
    ]


def claims(bt: dict) -> list:
    """문장이 주장하는 관계. 숫자가 조금 움직이는 것보다 이쪽이 중요하다 —
    이 관계가 깨지면 문단을 통째로 다시 써야 한다."""
    y = bt["indices"]["spx"]["curve"]["fng"]["h"]["1Y"]
    return [
        ("평균이 중앙값보다 훨씬 크다 (그래서 중앙값으로 긋는다)",
         y["avg"][0] > y["med"][0] * 1.5,
         f"평균 {y['avg'][0]:.2f}% · 중앙값 {y['med'][0]:.2f}%"),
        ("같은 '극단적 공포' 칸 안에서도 승률이 크게 갈린다",
         y["win"][5] - y["win"][24] >= 8,
         f"지수 5 → {y['win'][5]:.0f}% · 지수 24 → {y['win'][24]:.0f}% "
         f"(차이 {y['win'][5]-y['win'][24]:.0f}%p)"),
        ("VIX 표본이 공포탐욕보다 두 배 넘게 길다 (VIX 를 넣은 이유)",
         bt["indices"]["spx"]["curve"]["vix"]["days"]
         > bt["indices"]["spx"]["curve"]["fng"]["days"] * 2,
         f"VIX {bt['indices']['spx']['curve']['vix']['days']:,}일 · "
         f"공포탐욕 {bt['indices']['spx']['curve']['fng']['days']:,}일"),
    ]


def main() -> int:
    html = HTML.read_text(encoding="utf-8")
    bt = json.loads(BT.read_text(encoding="utf-8"))
    txt = prose(html)
    warn = err = 0

    print(f"설명 글의 숫자 대조  (backtest.json 갱신 {bt['updated'][:10]})\n")
    print(f"  {'항목':32s} {'글(한)':>9s} {'글(영)':>9s} {'실제':>9s}  판정")
    print("  " + "─" * 72)

    for name, rk, re_, actual, tol, dp in build(bt):
        ko = grab(txt["ko"], rk, name, "한국어")
        en = grab(txt["en"], re_, name, "영어")
        f = lambda v: f"{v:,.{dp}f}"
        if abs(ko - en) > 1e-9:
            mark, note = ERR, "두 언어가 다름"
            err += 1
        elif abs(ko - actual) > tol:
            mark, note = ERR, f"{abs(ko-actual):,.{dp}f} 벌어짐"
            err += 1
        elif abs(ko - round(actual, dp)) > 1e-9:
            mark, note = WARN, f"{abs(ko-actual):,.{max(dp,2)}f} 차이(허용 안)"
            warn += 1
        else:
            mark, note = OK, ""
        print(f"  {name:32s} {f(ko):>9s} {f(en):>9s} {f(actual):>9s}  {mark} {note}")

    print("\n  문장이 주장하는 것")
    for name, held, detail in claims(bt):
        if not held:
            err += 1
        print(f"    {OK if held else ERR} {name}")
        print(f"       {detail}")

    print()
    if err:
        print(f"오류 {err}건 — 설명 글을 고쳐야 합니다.")
        print("  `.about` 문단은 사전이 아니라 index.html 에 직접 박혀 있습니다.")
        print("  두 언어를 같이 고치세요. 논지가 깨졌다면 문단을 다시 쓰세요.")
        return 1
    if warn:
        print(f"경고 {warn}건 — 아직 오해를 부를 정도는 아니지만 자릿수가 어긋났습니다.")
        return 0
    print("전부 맞습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
