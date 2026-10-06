"""Keep disclosures as originally published, never backdate an amendment."""
import copy
from collections import defaultdict

BASE_PERIOD = "2024-09-30"


def shares(holdings):
    return [{k: h[k] for k in ("cusip", "name", "class", "shares", "value")}
            for h in holdings if (h.get("type") or "SH").strip().upper() == "SH"
            and not str(h.get("putCall") or "").strip()]


def collect(book, saved, reader, recent):
    """Unamended saved quarters are original; fetch originals for amended ones.

    reader(accession, filed) returns folded USD holdings and amendment type.
    recent() supplies dates for new amendments; cached disclosures need no SEC request.
    """
    known = {x["accession"]: x for x in saved}
    metadata = None
    expected = set()
    for q in book["quarters"]:
        if q["period"] < BASE_PERIOD:
            continue
        for acc in [q["accession"], *q.get("amended_by", [])]:
            expected.add(acc)
            if acc in known:
                continue
            regular = acc == q["accession"]
            if not regular and metadata is None:
                metadata = {x["accession"]: x for x in recent()}
            filed = q["filed"] if regular else (metadata.get(acc) or {}).get("filed")
            if not filed:
                raise ValueError(f"{acc}: missing public filing date")
            if regular and not q.get("amended_by"):
                holdings, kind = shares(q["holdings"]), "ORIGINAL"
            else:
                holdings, kind = reader(acc, filed)
                holdings = shares(holdings)
                if regular:
                    kind = "ORIGINAL"
            if kind not in ("ORIGINAL", "RESTATEMENT", "NEW HOLDINGS") or not holdings:
                raise ValueError(f"{acc}: incomplete/unknown disclosure")
            known[acc] = {"accession": acc, "period": q["period"], "filed": filed,
                          "kind": kind, "holdings": holdings}
    if not expected or not set(known).issubset(expected):
        raise ValueError("disclosure list shrank; retaining old data")
    return sorted(known.values(), key=lambda x: (x["filed"], x["period"], x["kind"] != "ORIGINAL", x["accession"]))


def timeline(disclosures, symbols):
    """Latest quarter known on each public date. Old amendments cannot rewind it."""
    states, result = {}, []
    grouped = defaultdict(list)
    for d in disclosures:
        grouped[d["filed"]].append(d)
    previous = None
    for filed, docs in sorted(grouped.items()):
        for d in sorted(docs, key=lambda x: (x["period"], x["kind"] != "ORIGINAL", x["accession"])):
            period = d["period"]
            if d["kind"] == "NEW HOLDINGS":
                if period not in states:
                    raise ValueError("amendment without original")
                merged = {h["cusip"]: copy.deepcopy(h) for h in states[period]}
                for h in d["holdings"]:
                    if h["cusip"] in merged:
                        merged[h["cusip"]]["shares"] += h["shares"]
                        merged[h["cusip"]]["value"] += h["value"]
                    else:
                        merged[h["cusip"]] = copy.deepcopy(h)
                states[period] = list(merged.values())
            else:
                states[period] = copy.deepcopy(d["holdings"])
        latest = max(states)
        holdings = []
        seen = set()
        for h in states[latest]:
            ticker = symbols[h["cusip"]]
            if ticker in seen:
                raise ValueError(f"{ticker}: ambiguous share-class mapping")
            seen.add(ticker)
            holdings.append({**h, "key": ticker, "ticker": ticker})
        state = {"period": latest, "holdings": sorted(holdings, key=lambda h: h["key"])}
        if state == previous:
            continue
        result.append({**state, "filed": filed, "accessions": [d["accession"] for d in docs]})
        previous = state
    return result


def candidates(events):
    """Only new entries after the baseline can start Alicia's positions."""
    found = set()
    prior = {h["key"] for h in events[0]["holdings"]}
    for e in events[1:]:
        current = {h["key"] for h in e["holdings"]}
        found.update(current - prior)
        prior = current
    return found
