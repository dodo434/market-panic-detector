"""Keep positive links at or above the selected correlation cutoff."""

import numpy as np


def threshold_edges(matrix: np.ndarray, pairs: np.ndarray, cutoff: float) -> np.ndarray:
    return pairs[matrix[pairs[:, 0], pairs[:, 1]] >= cutoff]
