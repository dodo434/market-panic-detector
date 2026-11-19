"""Background workers for downloads and metric computation."""

from __future__ import annotations

from datetime import date

import pandas as pd
from PySide6.QtCore import QObject, Signal

from data import compute_log_returns, download_alpaca_bars
from metrics import rolling_metrics


class AnalysisWorker(QObject):
    """Run data loading and rolling analysis outside the Qt UI thread."""

    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, tickers: list[str], start: date, cache_path: str, window: int) -> None:
        super().__init__()
        self.tickers = tickers
        self.start = start
        self.cache_path = cache_path
        self.window = window

    def run(self) -> None:
        try:
            self.progress.emit(10, "Loading market data...")
            prices, dropped = download_alpaca_bars(
                self.tickers,
                self.start,
                date.today(),
                cache_path=self.cache_path,
            )
            self.progress.emit(55, "Computing daily returns...")
            returns = compute_log_returns(prices)
            self.progress.emit(75, f"Calculating {self.window}-day windows...")
            metrics, matrices = rolling_metrics(returns, self.window)
            self.progress.emit(100, "Ready")
            self.finished.emit(
                {
                    "prices": prices,
                    "returns": returns,
                    "dropped": dropped,
                    "metrics": metrics,
                    "matrices": matrices,
                }
            )
        except Exception as exc:
            self.failed.emit(str(exc))
