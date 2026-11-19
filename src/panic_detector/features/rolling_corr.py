"""Pearson correlations calculated from complete, nonconstant windows."""

from collections.abc import Iterator
import numpy as np
import pandas as pd


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Normalize covariance by each pair's standard deviations."""
    if len(returns) < 2 or returns.isna().any().any() or (returns.nunique() < 2).any():
        raise ValueError("Each stock needs at least two distinct returns on matching dates.")
    return returns.corr()


def average_correlation(correlation: np.ndarray | pd.DataFrame) -> float:
    """Each unordered pair counts once and self-correlations count zero times."""
    matrix = np.asarray(correlation)
    return float(matrix[np.triu_indices(len(matrix), 1)].mean())


def windows(returns: pd.DataFrame, window: int) -> Iterator[tuple[pd.Timestamp, np.ndarray]]:
    """Skip incomplete or constant windows to keep N fixed and the spectrum meaningful."""
    if window < 2 or returns.shape[1] < 2:
        raise ValueError("Choose at least two stocks and a longer trading window.")
    data = returns.to_numpy(dtype=float)
    for end in range(window, len(data) + 1):
        sample = data[end - window : end]
        if np.isfinite(sample).all() and (np.ptp(sample, axis=0) > 0).all():
            matrix = np.corrcoef(sample.T)
            np.fill_diagonal(matrix, 1)
            yield pd.Timestamp(returns.index[end - 1]), matrix
