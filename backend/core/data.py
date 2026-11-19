from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timezone

import numpy as np
import pandas as pd


class MarketDataProvider:
    """Market data adapter with deterministic offline fallback and memory caching."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int], pd.DataFrame] = {}
        self._lock = threading.Lock()

    def history(self, asset: str, days: int = 180) -> pd.DataFrame:
        key = (asset.upper(), days)
        with self._lock:
            if key in self._cache:
                return self._cache[key].copy()
        frame = self._load_remote(asset, days)
        with self._lock:
            self._cache[key] = frame
        return frame.copy()

    def _load_remote(self, asset: str, days: int) -> pd.DataFrame:
        try:
            import yfinance as yf

            frame = yf.download(asset, period=f"{days}d", auto_adjust=False, progress=False)
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)
            frame = frame.rename(columns={"Adj Close": "adj_close", "Close": "close"})
            frame = frame[["close", "High", "Low", "Open", "Volume"]].rename(
                columns={"High": "high", "Low": "low", "Open": "open", "Volume": "volume"}
            )
            frame = frame.dropna()
            if len(frame) >= 30:
                frame.index = pd.to_datetime(frame.index).tz_localize(None)
                return frame
        except Exception:
            pass
        return self._synthetic(asset, days)

    @staticmethod
    def _synthetic(asset: str, days: int) -> pd.DataFrame:
        seed = int(hashlib.sha256(asset.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range(
            end=datetime.now(timezone.utc).date(), periods=days, normalize=True
        )
        drift = 0.00035 + (seed % 13) / 100000
        volatility = 0.012 + (seed % 7) / 1000
        returns = rng.normal(drift, volatility, len(dates))
        close = 100 * np.exp(np.cumsum(returns))
        frame = pd.DataFrame(index=dates)
        frame["close"] = close
        frame["open"] = close * (1 + rng.normal(0, 0.003, len(dates)))
        frame["high"] = frame[["open", "close"]].max(axis=1) * (1 + rng.uniform(0, 0.012, len(dates)))
        frame["low"] = frame[["open", "close"]].min(axis=1) * (1 - rng.uniform(0, 0.012, len(dates)))
        frame["volume"] = rng.integers(1_000_000, 10_000_000, len(dates))
        return frame


def returns(frame: pd.DataFrame) -> pd.Series:
    return np.log(frame["close"]).diff().dropna()
