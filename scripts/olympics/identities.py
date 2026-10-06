"""Verified retired identifiers, for baseline comparison only.

Nasdaq ECA2025-662: Liberty Live's 1:1 redemption reused LLYVA/LLYVK.
https://www.nasdaqtrader.com/TraderNews.aspx?id=eca2025-662
Nasdaq ECA2023-420: Formula One C reused FWONK after reclassification.
https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2023-420
These holdings predate this race; no retired-security price is synthesized.
"""
RETIRED = {"531229722": "LLYVK", "531229748": "LLYVA", "531229854": "FWONK"}
CLASSES = {"531229722": "COM LBTY LIV S C", "531229748": "COM LBTY LIV S A", "531229854": "COM SER C FRMLA"}


def baseline_aliases(required):
    result = {}
    for cusip, ticker in RETIRED.items():
        if cusip in required:
            if ("LIBERTY MEDIA" not in required[cusip]["name"].upper()
                    or required[cusip]["class"].strip().upper() != CLASSES[cusip]):
                raise ValueError(f"{cusip}: retired identity changed")
            result[cusip] = ticker
    return result
