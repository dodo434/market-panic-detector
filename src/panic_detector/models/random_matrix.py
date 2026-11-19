"""Marchenko-Pastur noise baseline."""

from __future__ import annotations

import numpy as np


def marchenko_pastur_upper_bound(n_assets: int, window: int) -> float:
    """Upper edge of noise: (1 + sqrt(N/T))^2 for N assets and T observations."""
    if n_assets <= 0 or window <= 0:
        raise ValueError("n_assets and window must be positive")
    return float((1.0 + np.sqrt(n_assets / window)) ** 2)
