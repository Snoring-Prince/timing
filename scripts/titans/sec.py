"""Small SEC client and pure filing-list parser shared by watcher and collector."""
import json
import time
import urllib.error
import urllib.request

PAUSE = 0.25


def user_agent(contact):
    return f"itpaidoff.com 13F fetcher ({contact})"


def get(url, contact, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": user_agent(contact),
                "Accept": "application/json,application/xml,*/*",
                "Accept-Encoding": "identity",
            })
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code} {exc.reason}"
            if exc.code not in (429, 500, 502, 503, 504) or attempt == tries-1:
                break
            time.sleep(3.0*(attempt+1))
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5*(attempt+1))
        finally:
            time.sleep(PAUSE)
    print(f"    받지 못했습니다: {last}\n      {url}")
    return None


def form_rows(block, forms=("13F-HR", "13F-HR/A")):
    result = []
    all_forms = block.get("form") or []
    for index, form in enumerate(all_forms):
        if form not in forms:
            continue
        def field(key):
            values = block.get(key) or []
            return values[index] if index < len(values) else None
        accession = field("accessionNumber")
        period = field("reportDate")
        if accession and period:
            result.append({"form": form, "filed": field("filingDate"),
                           "period": period, "accession": accession})
    return result


def recent_filings(cik, contact, getter=get):
    body = getter(f"https://data.sec.gov/submissions/CIK{cik}.json", contact)
    if not body:
        raise RuntimeError("SEC 제출 목록을 받지 못했습니다")
    payload = json.loads(body)
    rows = form_rows(((payload.get("filings") or {}).get("recent") or {}))
    if not rows:
        raise RuntimeError("SEC 최신 제출 목록에 13F가 없습니다")
    return rows
