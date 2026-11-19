"""Correlation, eigenvalue, and rolling-risk metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Return a clean sample correlation matrix."""
    matrix = returns.corr().replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="all").dropna(axis=1, how="all")
    matrix = matrix.reindex(index=matrix.columns, columns=matrix.columns)
    np_array = matrix.to_numpy(dtype=float)
    np_array = (np_array + np_array.T) / 2
    np.fill_diagonal(np_array, 1.0)
    np_array = np.clip(np_array, -1.0, 1.0)
    return pd.DataFrame(np_array, index=matrix.index, columns=matrix.columns)


def average_correlation(correlation: np.ndarray | pd.DataFrame) -> float:
    """Return the mean of the off-diagonal correlation entries."""
    values = np.asarray(correlation, dtype=float)
    n = values.shape[0]
    if n < 2:
        return 0.0
    off_diagonal = values[~np.eye(n, dtype=bool)]
    return float(np.nanmean(off_diagonal))


def top_eigenvalue(correlation: np.ndarray | pd.DataFrame) -> float:
    """Return the largest eigenvalue of a correlation matrix."""
    values = np.asarray(correlation, dtype=float)
    eigenvalues = np.linalg.eigvalsh((values + values.T) / 2)
    return float(eigenvalues[-1])


def marchenko_pastur_upper_bound(n_assets: int, window: int) -> float:
    """Return the Marchenko-Pastur upper eigenvalue bound."""
    if n_assets <= 0 or window <= 0:
        raise ValueError("n_assets and window must be positive")
    return (1.0 + np.sqrt(n_assets / window)) ** 2


def status_thresholds(shares: pd.Series | np.ndarray) -> tuple[float, float]:
    """Return percentile thresholds for elevated and panic statuses."""
    values = np.asarray(shares, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return (0.60, 0.75)
    return (float(np.nanpercentile(values, 75)), float(np.nanpercentile(values, 90)))


def classify_status(eigenvalue_share: float, elevated: float, panic: float) -> str:
    """Classify market stress using historical percentile thresholds."""
    if eigenvalue_share >= panic:
        return "PANIC"
    if eigenvalue_share >= elevated:
        return "ELEVATED"
    return "CALM"


def rolling_metrics(returns: pd.DataFrame, window: int = 60) -> tuple[pd.DataFrame, dict[tuple[pd.Timestamp, pd.Timestamp], pd.DataFrame]]:
    """Calculate rolling average correlation and top eigenvalue plus matrices."""
    rows: list[dict[str, float | pd.Timestamp]] = []
    matrices: dict[tuple[pd.Timestamp, pd.Timestamp], pd.DataFrame] = {}
    n_assets = len(returns.columns)

    for end_pos in range(window, len(returns) + 1):
        sample = returns.iloc[end_pos - window:end_pos].dropna(axis=1, thresh=window)
        if len(sample.columns) < 2:
            continue
        corr = correlation_matrix(sample)
        if corr.shape[0] != n_assets:
            corr = corr.reindex(index=returns.columns, columns=returns.columns)
            corr = corr.dropna(axis=0, how="all").dropna(axis=1, how="all")
        lambda_max = top_eigenvalue(corr)
        avg_corr = average_correlation(corr)
        end_date = pd.Timestamp(returns.index[end_pos - 1])
        start_date = pd.Timestamp(returns.index[end_pos - window])
        rows.append({
            "date": end_date,
            "average_correlation": avg_corr,
            "top_eigenvalue": lambda_max,
            "eigenvalue_share": lambda_max / len(corr),
            "mp_upper_bound": marchenko_pastur_upper_bound(len(corr), window),
        })
        matrices[(start_date, end_date)] = corr

    result = pd.DataFrame(rows).set_index("date")
    return result, matrices
