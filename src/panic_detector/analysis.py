"""One date-addressable numeric record per complete window. No GUI or I/O."""

import numpy as np
import pandas as pd
from panic_detector.features.returns import daily_log_returns
from panic_detector.features.rolling_corr import average_correlation, windows
from panic_detector.models.eigen import top_eigenvalue
from panic_detector.models.random_matrix import marchenko_pastur_upper_bound
from panic_detector.models.panic_score import historical_levels
from panic_detector.networks.layout import anchors, positions
from panic_detector.networks.mst import tree_edges


def analyze(prices: pd.DataFrame, window: int) -> np.ndarray:
    """N rows of the correlation matrix have trace N, hence leading share λ/N."""
    n = len(prices.columns)
    if n < 2:
        raise ValueError("Choose at least two stocks with sufficient shared history.")
    dtype = np.dtype(
        [
            ("date", "U10"),
            ("average", "f8"),
            ("leading", "f8"),
            ("share", "f8"),
            ("noise", "f8"),
            ("level", "f8"),
            ("corr", "f4", (n, n)),
            ("xy", "f4", (3, n, 2)),
            ("mst", "i2", (n - 1, 2)),
            ("symbols", [(str(s), "u1") for s in prices.columns]),
        ]
    )
    records = np.empty(max(0, len(prices) - window), dtype=dtype)
    count = 0
    for day, matrix in windows(daily_log_returns(prices), window):
        if count == 0:
            base = anchors(matrix)
        row = records[count]
        leading = top_eigenvalue(matrix)
        row["date"] = str(day.date())
        row["leading"], row["average"], row["share"] = (
            leading,
            average_correlation(matrix),
            leading / n,
        )
        row["noise"] = marchenko_pastur_upper_bound(n, window)
        row["corr"], row["xy"], row["mst"] = matrix, positions(base, matrix), tree_edges(matrix)
        row["symbols"] = tuple(0 for _ in prices.columns)
        count += 1
    if not count:
        raise ValueError("Choose a shorter window or stocks with more shared history.")
    records = records[:count]
    records["level"] = historical_levels(records["share"])
    return records
