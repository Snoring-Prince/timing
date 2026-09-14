"""
대가들의 선택 — SEC 13F 정찰(probe)

이 스크립트는 **파서가 아닙니다.** 받아서 재고 원본을 그대로 저장할 뿐입니다.

왜 이런 것이 따로 필요한가:

  1) 개발 환경에서는 SEC 에 닿지 않습니다. 야후와 같은 상황입니다
     (`CLAUDE.md` 3번). 실측 — www.sec.gov:443 / data.sec.gov:443 둘 다
     프록시가 403 으로 끊습니다(2026-09-14). **GitHub Actions 러너는 됩니다.**
  2) 그래서 응답이 어떻게 생겼는지를 **기억으로 짐작해서 파서를 짜면 안 됩니다.**
     이 프로젝트에는 추측 진단이 틀린 기록이 여러 번 있습니다(`CLAUDE.md` 0번).
     러너에서 한 번 받아 원본을 아티팩트로 올려 두고, 그것을 읽은 뒤에
     JSON 구조를 설계합니다.

받는 순서 (셋 다 원본을 저장합니다)

  A  data.sec.gov/submissions/CIK##########.json   제출 목록
  B  그 목록에서 가장 최근 13F-HR 를 찾아 그 폴더의 index.json
  C  폴더 안의 파일들 (크기 제한 안쪽)

SEC 는 이름 없는 요청을 거절합니다. User-Agent 에 연락처를 밝혀야 합니다.
이 저장소는 공개라 주소를 코드에 박으면 긁힙니다. 그래서 비밀값으로 받습니다.

    저장소 Settings → Secrets and variables → Actions
      SEC_CONTACT   SEC 에 밝힐 연락처 메일 주소

**비밀값이 없으면 종료코드 1 로 끝냅니다.** `notify.py --test` 와 같은 이유입니다 —
손으로 돌리는 것은 "되는지 확인해 달라"는 뜻이라, 조용히 넘어가면 **초록불인데
아무것도 안 받아온** 상태가 되어 설정이 된 건지 아닌지 알 수가 없습니다.

저장 위치: scripts/probe_sec.py
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# 버크셔 해서웨이. 첫 번째로 만드는 이유는 `docs/masters-13f.md` 4번에 있습니다 —
# 연차보고서에 보유 종목과 취득원가가 함께 나오는 유일한 곳이라, 우리 계산이
# 맞는지 대조할 수 있습니다.
CIK_DEFAULT = "0001067983"
FORM_DEFAULT = "13F-HR"

OUT_DIR = "sec-probe"

# SEC 는 초당 10건을 넘지 말라고 합니다. 넉넉히 띄웁니다 — 이 정찰은
# 스무 건 안쪽이라 느려져도 상관없습니다.
PAUSE = 0.25

# 한 파일이 이보다 크면 받지 않고 크기만 적습니다. 13F 정보표는 보통
# 수십 KB 라 걸릴 일이 없지만, 무엇이 들었는지 모르는 폴더를 훑는 중입니다.
MAX_BYTES = 8 * 1024 * 1024


def ua(contact: str) -> str:
    """SEC 가 요구하는 형식: 누가 쓰는지 + 연락처."""
    return f"itpaidoff.com 13F research probe ({contact})"


def get(url: str, contact: str, tries: int = 3) -> dict:
    """한 번 받아서 기록을 돌려줍니다. HTTP 오류로 죽지 않습니다."""
    rec = {"url": url, "ok": False, "status": None, "bytes": 0,
           "headers": {}, "error": None}
    body = b""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua(contact),
                "Accept": "application/json,text/html,application/xml,*/*",
                # gzip 을 요청하면 urllib 은 풀어 주지 않습니다. 크기가 작아
                # 압축이 필요 없으므로 아예 요청하지 않습니다.
                "Accept-Encoding": "identity",
            })
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
                rec["ok"] = True
                rec["status"] = r.status
                rec["headers"] = {k: v for k, v in r.headers.items()
                                  if k.lower() in ("content-type", "content-length",
                                                   "last-modified", "etag")}
            break
        except urllib.error.HTTPError as e:            # noqa: PERF203
            rec["status"] = e.code
            rec["error"] = f"HTTP {e.code} {e.reason}"
            try:
                body = e.read()[:4096]
            except Exception:                          # noqa: BLE001
                body = b""
            # 429(너무 잦음)·5xx 는 기다렸다 다시 걸어 볼 값어치가 있습니다.
            # 403 은 User-Agent 를 거절한 것이라 다시 걸어도 같습니다.
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                time.sleep(3.0 * (i + 1))
                continue
            break
        except Exception as e:                         # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    else:
        rec["error"] = f"{type(last).__name__}: {last}"

    rec["bytes"] = len(body)
    rec["_body"] = body
    time.sleep(PAUSE)
    return rec


def safe(name: str) -> str:
    """목차가 준 이름을 그대로 경로에 쓰지 않습니다.

    SEC 가 그럴 리는 없지만, 남이 준 문자열로 경로를 만드는 자리입니다.
    폴더를 거슬러 올라가는 이름은 납작하게 폅니다."""
    name = name.replace("\\", "/").lstrip("/")
    if ".." in name.split("/"):
        return name.replace("/", "_")
    return name


def save(rec: dict, name: str) -> dict:
    """원본을 그대로 저장합니다. 아티팩트로 올라가는 것이 이것입니다."""
    path = os.path.join(OUT_DIR, safe(name))
    os.makedirs(os.path.dirname(path) or OUT_DIR, exist_ok=True)
    with open(path, "wb") as f:
        f.write(rec.get("_body", b""))
    out = {k: v for k, v in rec.items() if k != "_body"}
    out["saved"] = path
    return out


TAG = re.compile(rb"<\s*([A-Za-z_][\w.:-]*)")


def census(body: bytes) -> dict:
    """무엇이 들었는지만 셉니다. **파싱이 아닙니다** — 태그 이름과 개수뿐입니다.

    구조를 여기서 해석하지 않는 것이 요점입니다. 이 숫자를 보고 나서
    사람이 스키마를 설계합니다."""
    head = body[:400]
    kind = "unknown"
    if head.lstrip()[:1] in (b"{", b"["):
        kind = "json"
    elif b"<?xml" in head or b"<" in head:
        kind = "xml/html"

    out = {"kind": kind, "head": head[:200].decode("utf-8", "replace")}

    if kind == "json":
        try:
            v = json.loads(body)
        except Exception as e:                         # noqa: BLE001
            out["json_error"] = str(e)
            return out
        if isinstance(v, dict):
            out["keys"] = sorted(v.keys())
            # 제출 목록이면 최근 목록의 열 이름과 줄 수가 궁금합니다.
            recent = (v.get("filings") or {}).get("recent")
            if isinstance(recent, dict):
                out["filings.recent.keys"] = sorted(recent.keys())
                out["filings.recent.rows"] = len(recent.get("form") or [])
                out["filings.older_files"] = len((v.get("filings") or {}).get("files") or [])
        elif isinstance(v, list):
            out["list_len"] = len(v)
        return out

    counts = {}
    for m in TAG.finditer(body):
        t = m.group(1).decode("ascii", "replace")
        counts[t] = counts.get(t, 0) + 1
    out["tags"] = dict(sorted(counts.items(), key=lambda kv: -kv[1])[:40])
    out["tag_kinds"] = len(counts)
    return out


SMALL = 8 * 1024        # 이보다 작은 글자 파일은 통째로 찍습니다


def show(name: str, body: bytes, cen: dict, n: int) -> None:
    """받은 것을 로그에 그대로 보여 줍니다. **해석하지 않습니다.**

    되풀이되는 기록이 무엇인지도 정하지 않습니다 — **가장 많이 나온 태그**를
    그냥 고릅니다. 그것이 무슨 뜻인지는 사람이 보고 판단합니다."""
    if n <= 0 or cen.get("kind") == "json":
        return
    # .htm/.html 은 EDGAR 가 사람 보라고 만든 화면입니다. 자료가 아니라 껍데기라
    # 개수만 세고 넘어갑니다 — 로그에 200줄씩 쌓일 이유가 없습니다.
    if name.lower().endswith((".htm", ".html")):
        print(f"\n  ── {name} — 화면용 HTML 이라 개수만: "
              f"태그 {cen.get('tag_kinds')}종")
        return
    print(f"\n  ── {name} ─────────────────────────────────────────")
    tags = cen.get("tags") or {}
    print(f"  태그 {cen.get('tag_kinds')}종: " +
          ", ".join(f"{k}×{v}" for k, v in list(tags.items())[:25]))

    txt = body.decode("utf-8", "replace")
    if len(body) <= SMALL:
        print("  (작은 파일이라 통째로)")
        for line in txt.splitlines():
            print("  | " + line)
        return

    # 가장 많이 나온 태그를 기록 단위로 삼고 앞의 몇 개만 찍습니다.
    top = next((k for k in tags if tags[k] > 1), None)
    if not top:
        print("  | " + txt[:1500].replace("\n", "\n  | "))
        return
    blocks = re.findall(rf"<{re.escape(top)}\b.*?</{re.escape(top)}>", txt, re.S)
    print(f"  되풀이 단위로 보이는 것: <{top}> {len(blocks)}개 — 앞 {min(n, len(blocks))}개")
    for b in blocks[:n]:
        for line in b.splitlines():
            print("  | " + line)
        print("  |")
    head = txt[:txt.find(f"<{top}")] if f"<{top}" in txt else txt[:800]
    print("  머리 부분:")
    for line in head.strip().splitlines()[:25]:
        print("  | " + line)


def all_filings(sub: dict, form: str) -> list[dict]:
    """제출 목록에서 그 서식을 **전부** 찾습니다(최신이 앞).

    `filings.recent` 만 봅니다. 더 오래된 것은 `filings.files` 에 별도 파일로
    쪼개져 있고, 그 개수는 따로 찍습니다."""
    recent = (sub.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    out = []
    for i, f in enumerate(forms):
        if f != form:
            continue
        out.append({k: (recent.get(k) or [None] * len(forms))[i]
                    for k in ("form", "filingDate", "reportDate",
                              "accessionNumber", "primaryDocument", "size")})
    return out


def one_filing(cik_int: str, filing: dict, contact: str, tag: str,
               show_n: int, man: dict) -> bool:
    """한 건의 제출 폴더를 훑습니다 — 목차를 읽고, 그 안의 파일을 받습니다.

    **파일 이름을 짐작하지 않습니다.** 목차(index.json)가 주는 이름만 씁니다.
    첫 실행에서 보유 목록 파일이 `56757.xml` 이었습니다 — 규칙이 없는 숫자라
    박아 두면 다음 분기에 깨집니다."""
    acc = re.sub(r"\D", "", filing["accessionNumber"] or "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}"
    print(f"[{tag}] {filing['filingDate']} 제출 · {filing['reportDate']} 기준  {base}/index.json")

    rec = get(f"{base}/index.json", contact)
    body = rec.get("_body", b"")
    step = save(rec, f"{tag}-index.json")
    step["census"] = census(body)
    man["steps"].append(step)
    print(f"    {rec['status']}  {rec['bytes']:,} bytes  {rec['error'] or ''}")
    if not rec["ok"]:
        return False

    items = ((json.loads(body).get("directory") or {}).get("item") or [])
    print(f"    파일 {len(items)}개")
    shown = []
    for it in items:
        name = it.get("name") or ""
        try:
            size = int(it.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if size > MAX_BYTES:
            print(f"    건너뜀 {name} — {size:,} bytes (제한 {MAX_BYTES:,})")
            man.setdefault("files", []).append({"name": name, "size": size,
                                                "skipped": "too large"})
            continue
        r = get(f"{base}/{name}", contact)
        b = r.get("_body", b"")
        f = save(r, os.path.join(f"{tag}-files", name))
        f["name"] = name
        f["census"] = census(b)
        man.setdefault("files", []).append(f)
        c = f["census"]
        extra = (f"{c.get('tag_kinds', '')} tag kinds" if c["kind"] != "json"
                 else f"keys={c.get('keys', [])[:8]}")
        print(f"    {name:<44} {r['status']} {r['bytes']:>10,} bytes  {c['kind']}  {extra}")
        shown.append((name, b, c))
    for name, b, c in shown:
        show(name, b, c, show_n)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="SEC 13F 정찰 — 받아서 재고 원본을 저장합니다")
    ap.add_argument("--cik", default=CIK_DEFAULT, help="10자리 CIK (기본: 버크셔)")
    ap.add_argument("--form", default=FORM_DEFAULT, help="서식 이름 (기본: 13F-HR)")
    # 아티팩트를 개발 환경에서 못 받습니다 — 내려받기 주소가 blob.core.windows.net 이고
    # 프록시가 403 으로 끊습니다(2026-09-14 실측). 로그는 읽을 수 있으므로
    # **내용을 로그에도 찍습니다.** 그러면 사람이 아티팩트를 받아 건네줄 필요가 없습니다.
    ap.add_argument("--show", type=int, default=3, help="되풀이되는 기록을 몇 개나 찍을지 (0=안 찍음)")
    ap.add_argument("--no-old", dest="old", action="store_false",
                    help="가장 오래된 건은 받지 않는다 (기본: 받아서 단위를 비교)")
    a = ap.parse_args()

    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        print("정찰을 할 수 없습니다 — 비밀값 SEC_CONTACT 가 없습니다.")
        print("  SEC 는 이름 없는 요청을 거절합니다. 연락처 메일 주소를 밝혀야 합니다.")
        print("  저장소 Settings → Secrets and variables → Actions 에서 넣어 주세요.")
        print("  SEC_CONTACT   SEC 에 밝힐 메일 주소")
        print("  (이 저장소는 공개라 코드에 주소를 박으면 긁힙니다. 그래서 비밀값입니다.)")
        return 1

    cik = re.sub(r"\D", "", a.cik).zfill(10)
    cik_int = str(int(cik))
    os.makedirs(OUT_DIR, exist_ok=True)

    man = {
        "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cik": cik, "form": a.form,
        "user_agent": ua("<SEC_CONTACT>"),   # 주소는 어디에도 적지 않습니다
        "steps": [],
    }

    # ── A. 제출 목록 ─────────────────────────────────────────────
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"[A] 제출 목록  {url}")
    rec = get(url, contact)
    body = rec.get("_body", b"")
    stepA = save(rec, "A-submissions.json")
    stepA["census"] = census(body)
    man["steps"].append(stepA)
    print(f"    {rec['status']}  {rec['bytes']:,} bytes  {rec['error'] or ''}")
    if not rec["ok"]:
        print("    → 여기서 멈춥니다. 위 상태 코드를 보고 판단하세요.")
        print("      403 이면 SEC 가 User-Agent 를 거절한 것입니다.")
        json.dump(man, open(os.path.join(OUT_DIR, "manifest.json"), "w"),
                  ensure_ascii=False, indent=2)
        return 1
    print(f"    {json.dumps(stepA['census'], ensure_ascii=False)[:400]}")

    sub = json.loads(body)
    got = all_filings(sub, a.form)
    older = len((sub.get("filings") or {}).get("files") or [])
    man["filings_found"] = got
    man["older_chunks"] = older
    if not got:
        print(f"    → {a.form} 을 최근 목록에서 못 찾았습니다.")
        json.dump(man, open(os.path.join(OUT_DIR, "manifest.json"), "w"),
                  ensure_ascii=False, indent=2)
        return 1

    # ── A-2. 그 서식이 몇 건이나, 언제까지 있나 ──────────────────
    # 이 사이트가 보여 줄 것은 "그래서 어떻게 됐나"라 **과거가 전부** 필요합니다.
    # 최근 목록에 몇 분기가 들어 있는지, 더 옛것이 따로 있는지를 먼저 봅니다.
    print(f"    최근 목록의 {a.form} {len(got)}건 "
          f"({got[-1]['reportDate']} ~ {got[0]['reportDate']})")
    print(f"    더 오래된 목록 파일 {older}개 (filings.files)")
    for f in got:
        print(f"      {f['filingDate']} 제출 · {f['reportDate']} 기준  "
              f"{f['accessionNumber']}  {f['size']:>8,} bytes")

    # ── B·C. 가장 최근 건 ───────────────────────────────────────
    if not one_filing(cik_int, got[0], contact, "new", a.show, man):
        json.dump(man, open(os.path.join(OUT_DIR, "manifest.json"), "w"),
                  ensure_ascii=False, indent=2)
        return 1

    # ── D. 가장 오래된 건 ───────────────────────────────────────
    # **단위가 바뀐 적이 있는지**를 봐야 합니다. 금액이 달러인지 천 달러인지가
    # 도중에 달라졌다면, 옛 분기가 1000배로 나옵니다. 날짜를 외워서 박지 말고
    # 두 끝을 실제로 받아서 비교합니다(최신 건은 금액÷주식수가 $45.95 로
    # 딱 떨어졌습니다 — 달러 단위라는 뜻입니다).
    if a.old and len(got) > 1:
        print()
        one_filing(cik_int, got[-1], contact, "old", a.show, man)

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)

    print()
    print(f"원본을 {OUT_DIR}/ 에 저장했고(아티팩트), 위에 그대로 찍었습니다.")
    print("이것을 읽고 나서 JSON 구조를 설계합니다.")
    print("이 스크립트는 아무것도 해석하지 않았습니다 — 받고, 세고, 보여 줬을 뿐입니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
