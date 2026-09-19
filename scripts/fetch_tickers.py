#!/usr/bin/env python3
"""CUSIP → 티커. 로고를 찾는 데 쓰는 마지막 조각입니다.

왜 필요한가
-----------
화면(`titans/index.html`)은 로고를 **ISIN** 으로 찾습니다. 미국 종목의 ISIN 은
"US" + CUSIP 아홉 자리 + 체크숫자라서 공시만 있으면 계산됩니다 — 표가 필요 없습니다.

**그런데 미국 발행사가 아니면 그 계산이 안 됩니다.** CUSIP 첫 글자가 숫자가 아닌
것들(CINS)인데, 버뮤다·케이맨·아일랜드·스위스 법인이 여기 해당합니다.
28년치 223개 묶음 중 13개(5.8%)가 그렇고, 지금 보유 중인 것은 처브 하나입니다.

손으로 적어 넣을 수도 있지만 **매니저를 더 넣으면 계속 늘어납니다.** 사람이
붙어야 하는 표는 결국 낡습니다. 그래서 기계가 채웁니다.

어디서 받나
-----------
**OpenFIGI** (Bloomberg 가 여는 표준). CUSIP 으로 티커를 찾는 용도로 만들어진
곳이고 키 없이 씁니다(키 없을 때 분당 25요청 · 요청당 10건).
**여기서 받아 저장소에 두고, 방문자 브라우저는 이 파일만 읽습니다** — 방문자가
OpenFIGI 로 직접 나가지 않으므로 IP 도 안 새고 화면이 그쪽에 묶이지도 않습니다.

**개발 환경에서는 막혀 있습니다**(`000`). 러너에서 돌려야 합니다 — SEC·야후와 같습니다.

이미 물어본 것은 다시 묻지 않습니다
-----------------------------------
찾은 것은 티커를, **못 찾은 것은 빈 문자열을** 적어 둡니다. 옛 종목의 사라진
주식 종류(리버티글로벌 4종 같은 것)는 OpenFIGI 에도 없어서 영영 못 찾는데,
그걸 기록하지 않으면 **매주 다시 묻고 매주 실패합니다.** 이 프로젝트가 이미
적어 둔 함정입니다 — "매주 실패하면 아무도 안 봅니다"(CLAUDE.md 6-2).

못 찾은 것도 `RETRY_DAYS` 뒤에는 한 번 더 물어봅니다. 나중에 등록될 수 있으니까요.

**실패로 끝내는 경우는 하나뿐입니다**: 한 번도 안 물어본 종목이 있는데 그중
하나도 못 받았을 때. 그때는 OpenFIGI 가 막혔다는 뜻이라 빨간 X 로 보여야 합니다.
옛 종목이 계속 안 잡히는 것은 실패가 아닙니다.

**`_` 로 시작하는 키는 화면이 무시합니다.** 파일에 언제 물어봤는지를 같이 둡니다.
"""
import datetime as dt
import gzip, json, os, re, sys, time, urllib.request, urllib.error, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from titans.registry import books  # noqa: E402

OUT  = ROOT / "data" / "titans" / "tickers.json"
API  = "https://api.openfigi.com/v3/mapping"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
BATCH = 10          # 키 없을 때 요청당 최대 10건
PAUSE = 3.0         # 분당 25요청 한도 — 넉넉히 띄운다
RETRY_DAYS = 90     # 못 찾은 것을 다시 물어보기까지
# **출처를 새로 붙이면 이 값을 올리세요.** 못 찾은 것은 빈 값으로 굳어 있어서
# 그냥 두면 90일 뒤에나 다시 물어봅니다. SEC 대조를 새로 넣은 지금이 그 경우라,
# 파일의 _asked 를 지우는 대신 여기서 세대를 올려 한 번 다시 돌게 합니다.
# **sec → sec2 로 올린 이유**: 첫 실행에서 SEC 표를 gzip 인 채로 json.loads 에
# 넣어 열다섯 건이 전부 '못 찾음' 으로 굳었습니다. 이름이 안 맞아서가 아니라
# 표를 읽지도 못한 것이라, 고친 뒤 한 번 다시 물어봐야 합니다.
SOURCES = "openfigi+sec3"  # 바뀌면 못 찾은 것을 전부 다시 물어봅니다


# ── SEC 회사 이름 → 티커 ───────────────────────────────────────────
# OpenFIGI 가 CINS 를 모른다는 것이 두 번의 실행으로 확인됐습니다
# (ID_CUSIP · ID_CUSIP_8_CHR 둘 다 No identifier found).
#
# 그래서 **이름으로 찾습니다.** SEC 가 회사 이름·티커·CIK 표를 공개하고,
# 이 저장소는 이미 SEC_CONTACT 를 갖고 있습니다(새 열쇠가 필요 없습니다).
#
# **로고는 발행사만 맞으면 됩니다.** 리버티글로벌 네 종류는 전부 같은 회사이고
# 로고도 하나입니다. 그래서 주식 종류를 못 가려도 상관없습니다 — 값을 다루는
# 일이었다면 이 방식을 쓰지 않았을 겁니다.
#
# **한 회사로 좁혀질 때만 받습니다.** 이름이 여러 회사에 걸리면 버립니다.
# 엉뚱한 회사 로고를 다는 것보다 글자 타일이 낫습니다.
SUFFIX = {"LTD","LIMITED","PLC","INC","INCORPORATED","CORP","CORPORATION",
          "CO","COMPANY","HLDGS","HOLDINGS","HOLDING","GROUP","GRP",
          "NEW","DEL","THE","SA","NV","AG","LP","LLC","CLASS","CL",
          "OF","AND"}          # 13F 는 'BANK AMER', SEC 는 'BANK OF AMERICA'

# SEC 이름 끝에 붙는 설립 주 표식(`/DE/`, `/MD/`, `/NEW/`). 낱말로 남겨 두면
# 무디스가 ["MOODYS","DE"] 가 되어 공시의 ["MOODYS"] 와 안 맞습니다.
STATE = re.compile(r"\s*/[A-Za-z]{2,4}/?\s*$")


def norm(name: str):
    """이름을 비교할 수 있는 모양으로. 회사 형태 낱말은 버립니다."""
    # 아포스트로피는 **지웁니다**(공백으로 바꾸지 않습니다). 공백으로 바꾸면
    # SEC 의 `Moody's` 가 ["MOODY","S"] 가 되어 공시의 ["MOODYS"] 와 어긋납니다.
    t = re.sub(r"['\u2019]", "", STATE.sub("", str(name)))
    w = re.sub(r"[^A-Za-z0-9 ]", " ", t).upper().split()
    return [x for x in w if x and x not in SUFFIX]


# 열쇠는 **층으로 나눠서 같은 층끼리만 맞춥니다.** 층을 섞으면 넓은 열쇠가
# 좁은 열쇠를 이깁니다 — 첫 판에서 실제로 애플이 그렇게 떨어졌습니다.
# `APPLE INC` 의 통째 열쇠 `APPLE` 이, `Apple Hospitality REIT` 의 첫낱말
# 열쇠 `APPLE` 과 같은 칸에 들어가 **두 회사로 갈려서 버려졌습니다.**
# 층을 나누면 통째 열쇠 칸에는 애플 하나뿐이라 그대로 잡힙니다.
LEVELS = 6


def keys(name: str):
    """층별 열쇠. 자리(첨자)가 곧 층이고, 없는 층은 `None` 입니다.

    **공시의 이름은 줄여 쓰여 있고 낱말 순서도 다릅니다.**

    ```
    0 통째     APPLE            = Apple Inc.
    1 순서무시  D HORTON R       = HORTON D R INC  (SEC 은 성을 앞에 적습니다)
    2 붙여쓰기  SIRIUSXM         = Sirius XM
    3 앞 4자    BANK AMER        = BANK OF AMERICA
    4 앞 3자    OCC PET          = OCCIDENTAL PETROLEUM
    5 첫낱말    CHEVRON
    ```

    넓은 층일수록 엉뚱한 회사가 걸릴 수 있는데, **한 회사로 좁혀질 때만 받는
    규칙**이 그것을 막습니다 — 여럿이 걸리면 버리고 글자 타일로 갑니다.
    """
    w = norm(name)
    if not w:
        return [None] * LEVELS
    # **한 낱말이어도 1·2층은 비우지 않습니다.** 낱말이 하나면 순서무시도
    # 붙여쓰기도 그 낱말 자신인데, 비워 두면 공시의 `SIRIUSXM` 이 SEC 의
    # `Sirius XM`(붙여쓰기 열쇠 SIRIUSXM)과 만날 자리가 없어집니다.
    # 층을 나누면서 실제로 이 한 건이 떨어졌습니다.
    two = len(w) > 1
    return [
        " ".join(w),                                  # 0 통째
        " ".join(sorted(w)),                          # 1 순서무시
        "".join(w),                                   # 2 붙여쓰기
        f"{w[0][:4]} {w[1][:4]}" if two else None,    # 3 앞 4자
        f"{w[0][:3]} {w[1][:3]}" if two else None,    # 4 앞 3자
        w[0],                                         # 5 첫낱말
    ]


def sec_index(contact: str):
    """SEC 의 회사 이름 표를 받아 {정규화 이름: {cik: [티커…]}} 로 만듭니다."""
    req = urllib.request.Request(
        SEC_TICKERS, headers={"User-Agent": contact, "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=30) as r:
        enc = (r.headers.get("Content-Encoding") or "").lower()
        raw = r.read()
    # **압축을 풀어야 합니다.** urllib 은 자동으로 풀지 않습니다 — Accept-Encoding 을
    # 보내 놓고 그대로 json.loads 에 넣어서 첫 실행이 통째로 실패했습니다
    # (207KB 가 gzip 바이트로 들어와 JSONDecodeError). 헤더를 믿지 않고
    # **매직 바이트로도 확인**합니다. 안 보내도 압축해 주는 서버가 있습니다.
    if raw[:2] == b"\x1f\x8b" or "gzip" in enc:
        raw = gzip.decompress(raw)
    elif "deflate" in enc:
        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    text = raw.decode("utf-8", "replace")
    print(f"  SEC 표 {len(text):,} bytes · 앞부분 {text[:120]}", flush=True)

    rows = json.loads(text)
    # 형식을 짐작하지 않습니다 — 사전이든 목록이든 값만 훑습니다.
    items = rows.values() if isinstance(rows, dict) else rows
    idx = [{} for _ in range(LEVELS)]
    for it in items:
        if not isinstance(it, dict):
            continue
        t = str(it.get("ticker") or "").strip().upper()
        cik = it.get("cik_str") or it.get("cik")
        title = it.get("title") or it.get("name") or ""
        if not t or cik is None:
            continue
        for lv, key in enumerate(keys(title)):
            if key:
                idx[lv].setdefault(key, {}).setdefault(str(cik), []).append((t, title))
    return idx


def sec_lookup(idx, name):
    """전체 이름으로 먼저, 안 되면 앞 두 낱말로. 한 회사일 때만 돌려줍니다.

    돌려주는 것은 (티커, SEC 가 적은 이름, CIK). **CIK 를 같이 주는 이유**는
    섹터(SIC)가 CIK 로 따라오기 때문입니다 — `fetch_sectors.py` 가 씁니다.
    """
    for lv, key in enumerate(keys(name)):
        if not key:
            continue
        hit = idx[lv].get(key)                    # **같은 층끼리만** 맞춥니다
        if hit and len(hit) == 1:                 # 회사가 하나로 좁혀짐
            cik = next(iter(hit))
            pairs = sorted(hit[cik])
            return pairs[0][0], pairs[0][1], cik
    return None, None, None


def cusip_ok(c: str) -> bool:
    """CUSIP 아홉째 자리가 앞 여덟 자리에서 계산한 값과 맞는가.

    **OpenFIGI 가 이것을 검사합니다.** 첫 실행에서 한 건만
    `Invalid idValue format` 이 왔는데, 세어 보니 정확히 체크숫자가 틀린
    자리였습니다. 그런 것은 물어봐야 소용이 없으므로 보내지 않습니다.

    28년치에서 두 건이 걸립니다. **둘 다 올바른 짝이 자료 안에 따로 있습니다.**
      G47766101  Ingersoll-Rand 2006~2007 — 바른 값 G4776G101.
                 2013년 이전 텍스트 공시를 변환할 때 글자 G 를 숫자 6 으로 읽음.
      G6693N103  NU Holdings 2021~2022 — 바른 값 G6683N103.
                 XML 시대라 **SEC 원문 자체의 오타**입니다(나중 분기에 고쳐짐).
    """
    if len(c) != 9:
        return False
    tot = 0
    for i, ch in enumerate(c[:8].upper()):
        if ch.isdigit(): v = int(ch)
        elif ch.isalpha(): v = ord(ch) - 55
        elif ch == "*": v = 36
        elif ch == "@": v = 37
        elif ch == "#": v = 38
        else: return False
        if i % 2: v *= 2
        tot += v // 10 + v % 10
    return c[8].isdigit() and int(c[8]) == (10 - tot % 10) % 10


def needs_ticker(cusip: str) -> bool:
    """ISIN 을 만들 수 없는 것만 고른다.

    첫 글자가 숫자면 미국 발행사이고 화면이 ISIN 을 직접 계산한다.
    여기서 물을 이유가 없다 — 요청을 아끼는 것이 아니라, 물어볼 필요가 없다.
    """
    return len(cusip) == 9 and not cusip[0].isdigit()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def ask(cusips, id_type="ID_CUSIP"):
    """OpenFIGI 에 한 묶음을 묻는다. 돌려주는 것은 ({cusip: ticker}, 원본 조각).

    **원본을 같이 돌려줍니다.** 첫 실행에서 17개가 전부 '못 찾음' 으로 나왔는데
    로그에는 우리가 해석한 결과만 찍혀서 **저쪽이 실제로 뭐라고 했는지 알 수가
    없었습니다.** 개발 환경에서 OpenFIGI 가 막혀 있으니(`000`) 응답 모양을
    짐작해서 파서를 짠 셈이고, 그건 이 프로젝트가 `probe_sec.py` 를 만들면서
    하지 않기로 한 일입니다(CLAUDE.md 9-3). 이제 원본을 로그에 남깁니다.
    """
    # ID_CUSIP_8_CHR 은 체크숫자를 뗀 여덟 자리로 묻습니다.
    vals = [c[:8] if id_type == "ID_CUSIP_8_CHR" else c for c in cusips]
    body = json.dumps([{"idType": id_type, "idValue": v} for v in vals]).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "itpaidoff.com titans (github.com/Snoring-Prince/timing)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, text = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        # 오류 본문에 이유가 적혀 있는 경우가 많다. 삼키지 않는다.
        raise RuntimeError(f"HTTP {e.code} · {e.read().decode('utf-8','replace')[:300]}") from None

    raw = f"{id_type} · HTTP {status} · {text[:360]}"
    rows = json.loads(text)

    out = {}
    # 응답은 보낸 순서대로 온다. 항목마다 data(성공) 또는 warning(못 찾음).
    for cusip, row in zip(cusips, rows):
        hits = (row or {}).get("data") or []
        if not hits:
            continue
        # 한 CUSIP 에 거래소별로 여러 줄이 온다. 미국 상장분을 먼저 고른다 —
        # 13F 는 미국 상장 종목만 담으므로 그쪽이 화면에 찍히는 것과 맞는다.
        pick = next((h for h in hits if h.get("exchCode") == "US"), hits[0])
        t = (pick.get("ticker") or "").strip().upper()
        if t:
            out[cusip] = t
    return out, raw


def wanted_tickers(investor_books):
    """Return CUSIPs and their newest disclosed names across all investors."""
    # 등록된 모든 투자자의 전 기간에서 모은다. 옛 종목도 '일생' 화면에서 쓴다.
    wanted, name, named_at = set(), {}, {}
    for book in investor_books:
        for q in book["quarters"]:
            period = q.get("period", "")
            for h in q.get("holdings", []):
                c = h.get("cusip", "")
                if needs_ticker(c):
                    wanted.add(c)
                    if period >= named_at.get(c, ""):
                        name[c] = h.get("name", "")
                        named_at[c] = period
    return wanted, name


def main():
    investor_books = books()
    if not investor_books:
        print("투자자 공시 파일을 못 읽었습니다 — 티커는 건너뜁니다.")
        return 0
    wanted, name = wanted_tickers(investor_books)

    have = load_json(OUT, {})
    asked = have.pop("_asked", "")          # 화면이 무시하는 키. 쓸 때 다시 넣는다.
    today = dt.date.today()

    fresh = sorted(wanted - set(have))      # 한 번도 안 물어본 것
    stale = []                              # 못 찾았던 것 — 오래됐으면 한 번 더
    try:
        old = (today - dt.date.fromisoformat(asked)).days >= RETRY_DAYS
    except Exception:
        old = True
    if old or have.pop("_sources", "") != SOURCES:
        stale = sorted(c for c in wanted if c in have and not have[c])

    todo = fresh + stale
    print(f"ISIN 을 못 만드는 종목 {len(wanted)}개 · 아는 것 "
          f"{sum(1 for c in have.values() if c)}개 · 못 찾은 것 "
          f"{sum(1 for c in have.values() if not c)}개")
    print(f"물어볼 것 {len(todo)}개 (처음 {len(fresh)} · 다시 {len(stale)})")
    if not todo:
        print("새로 물어볼 것이 없습니다.")
        return 0

    # 체크숫자가 틀린 것은 보내 봐야 'Invalid idValue format' 만 돌아온다.
    broken = [c for c in todo if not cusip_ok(c)]
    todo = [c for c in todo if cusip_ok(c)]
    for c in broken:
        print(f"  {c}  {name.get(c,'')[:30]:<30} → 체크숫자가 틀린 CUSIP (묻지 않음)")

    # **두 가지 방식으로 물어봅니다.** 첫 실행에서 형식이 멀쩡한 CINS 열다섯 건이
    # 전부 'No identifier found' 였습니다. OpenFIGI 가 CINS 를 ID_CUSIP 으로는
    # 색인하지 않는 것으로 보이는데, 짐작만 하지 않고 문서에 있는 여덟 자리 방식
    # (ID_CUSIP_8_CHR)도 실제로 한 번 물어보고 원본을 남깁니다.
    got, failed, raws, answered = {}, [], {}, False
    for id_type in ("ID_CUSIP", "ID_CUSIP_8_CHR"):
        rest = [c for c in todo if c not in got]
        if not rest:
            break
        print(f"\n[{id_type}] {len(rest)}건", flush=True)
        for i in range(0, len(rest), BATCH):
            chunk = rest[i:i + BATCH]
            try:
                hits, raw = ask(chunk, id_type)
                got.update(hits)
                answered = True
                raws.setdefault(id_type, raw)   # 방식마다 원본 하나씩
            except Exception as e:
                print(f"  실패 {type(e).__name__}: {e}", flush=True)
                failed += chunk
            if i + BATCH < len(rest):
                time.sleep(PAUSE)
        print(f"  누적 {len(got)}건 찾음", flush=True)

    # ── OpenFIGI 가 모르는 것은 SEC 의 회사 이름 표로 찾습니다 ──────────
    rest = [c for c in todo if c not in got]
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if rest and contact:
        print(f"\n[SEC 이름 대조] {len(rest)}건", flush=True)
        try:
            idx = sec_index(contact)
            answered = True
            for c in rest:
                t, title, _cik = sec_lookup(idx, name.get(c, ""))
                if t:
                    got[c] = t
                    print(f"  {name.get(c,'')[:28]:<28} → {t}   (SEC: {title})", flush=True)
            print(f"  누적 {len(got)}건 찾음", flush=True)
        except Exception as e:
            print(f"  실패 {type(e).__name__}: {e}", flush=True)
    elif rest:
        # SEC 는 이름 없는 요청을 거절합니다. 비밀값이 없으면 이 길은 잠깁니다.
        print("\n[SEC 이름 대조] SEC_CONTACT 가 없어 건너뜁니다.", flush=True)

    for c in todo:
        print(f"  {c}  {name.get(c,'')[:30]:<30} → {got.get(c) or '못 찾음'}")

    # 하나도 못 받았으면 **저쪽이 실제로 보낸 것**을 보여 준다. 우리가 해석한
    # 결과만 찍으면 왜 비었는지 알 수 없다 — 첫 실행에서 실제로 그랬다.
    if not got:
        for r in raws.values():
            print(f"\n응답 원본: {r}", flush=True)

    # **실패로 끝내는 기준은 "답이 왔느냐" 하나뿐입니다.**
    # 처음에는 "하나도 못 찾으면 실패"로 뒀는데, 재 보니 OpenFIGI 는 멀쩡히
    # 답하면서 CINS 를 그냥 모른다고 합니다(HTTP 200 + No identifier found).
    # 그 상태로 실패를 내면 **새 해외 종목이 들어올 때마다 빨간 X** 가 뜨고,
    # 6-2 의 "매주 실패하면 아무도 안 봅니다"가 그대로 생깁니다.
    # 못 찾은 것은 빈 값으로 적어 두면 그만입니다 — 화면은 글자 타일로 갑니다.
    if todo and not answered:
        print("\nOpenFIGI 에 닿지 못했습니다 — 응답이 하나도 오지 않았습니다.",
              file=sys.stderr)
        return 1

    # 못 찾은 것도 빈 값으로 적어 둔다. 안 적으면 매주 다시 묻고 매주 실패한다.
    for c in todo + broken:
        have[c] = got.get(c, "")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    have["_asked"] = today.isoformat()
    have["_sources"] = SOURCES
    OUT.write_text(json.dumps(have, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    have.pop("_asked"); have.pop("_sources")
    try:
        where = OUT.relative_to(ROOT)
    except ValueError:          # 시험할 때 다른 자리에 쓰는 경우
        where = OUT
    print(f"\n{where} 에 {len(have)}개 저장 (이번에 새로 찾은 것 {len(got)}개)")
    if failed:
        print(f"못 받은 것 {len(failed)}개 — 다음 주에 다시 묻습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
