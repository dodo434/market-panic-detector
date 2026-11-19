"""The complete graph stores one signed correlation for each unordered stock pair."""

import numpy as np


def all_pairs(n: int) -> np.ndarray:
    return np.column_stack(np.triu_indices(n, 1)).astype(np.int16)
