"""Normalize exchange symbols before using them in requests or cache identities."""

import re
from collections.abc import Iterable

SYMBOL = re.compile(r"[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z0-9]{1,3})?", re.ASCII)


def validate_tickers(tickers: Iterable[str]) -> list[str]:
    entries = [s.strip() for s in tickers]
    if any(not s.isascii() for s in entries):
        raise ValueError("Use exchange symbols written with ASCII letters and digits.")
    symbols = list(dict.fromkeys(s.upper() for s in entries))
    if not 1 <= len(symbols) <= 50:
        raise ValueError("Choose between one and 50 different stock symbols.")
    if any(len(s) > 12 or not SYMBOL.fullmatch(s) for s in symbols):
        raise ValueError("Use stock symbols such as AAPL or BRK.B.")
    return symbols
