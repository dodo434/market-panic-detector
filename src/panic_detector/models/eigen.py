"""Measure the strongest common component in standardized stock returns."""

import numpy as np


def top_eigenvalue(correlation: np.ndarray) -> float:
    """For an equicorrelated N-stock basket the leading value is 1 + (N-1)ρ for ρ ≥ 0."""
    return float(np.linalg.eigvalsh(correlation)[-1])
