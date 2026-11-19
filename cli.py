"""Terminal fallback for the Market Panic Detector."""

from __future__ import annotations

from datetime import date

import pandas as pd

from data import DEFAULT_TICKERS, compute_log_returns, download_alpaca_bars
from metrics import rolling_metrics, status_thresholds, classify_status


def run_cli(
    tickers: list[str] | None = None,
    window: int = 60,
    cache_path: str = "cache/alpaca_daily.parquet",
) -> int:
    """Download/cached-load data and print the latest plain-English status."""
    try:
        prices, dropped = download_alpaca_bars(
            tickers or DEFAULT_TICKERS,
            date(2018, 1, 1),
            date.today(),
            cache_path=cache_path,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    returns = compute_log_returns(prices)
    metrics, _ = rolling_metrics(returns, window)
    if metrics.empty:
        print("ERROR: Not enough history to calculate a 60-day window.")
        return 1

    latest = pd.Timestamp(metrics.index[-1])
    row = metrics.loc[latest]
    elevated, panic = status_thresholds(metrics["eigenvalue_share"])
    status = classify_status(float(row["eigenvalue_share"]), elevated, panic)
    print(f"MARKET STATUS: {status}")
    print(f"Date: {latest.date()}")
    print(f"Average correlation: {row['average_correlation']:.3f}")
    print(f"Top eigenvalue: {row['top_eigenvalue']:.3f}")
    print(f"Share of market-wide variation: {row['eigenvalue_share']:.1%}")
    print(f"Elevated threshold: {elevated:.1%} | Panic threshold: {panic:.1%}")
    if dropped:
        print("Dropped tickers: " + ", ".join(dropped))
    return 0
