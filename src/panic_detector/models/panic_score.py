"""Rank common-factor strength against observations available on that date."""

from bisect import bisect_left, bisect_right, insort
from collections.abc import Iterable
import numpy as np


def historical_levels(shares: Iterable[float]) -> np.ndarray:
    """Prior-only empirical midrank. Ties receive half credit and the first score is 50."""
    history: list[float] = []
    levels = []
    for share in shares:
        below, through = bisect_left(history, share), bisect_right(history, share)
        levels.append(50 * (below + through) / len(history) if history else 50.0)
        insort(history, share)
    return np.array(levels)


def classify_status(level: float) -> str:
    if level < 50:
        return "CALM"
    return "PANIC" if level > 80 else "NERVOUS"
