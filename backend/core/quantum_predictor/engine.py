from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from backend.core.data import returns
from backend.core.schemas import ForecastPoint, QuantumResult


class QuantumPricePredictor:
    """Fast quantum-inspired probabilistic forecast.

    The implementation uses a drift/volatility state distribution and Monte
    Carlo paths. It is intentionally dependency-light and deterministic per
    input series, while leaving a stable boundary for a future quantum backend.
    """

    def predict(self, asset: str, frame: pd.DataFrame, horizon: int) -> QuantumResult:
        price = float(frame["close"].iloc[-1])
        series = returns(frame)
        drift = float(series.tail(30).mean())
        volatility = max(float(series.tail(60).std(ddof=0)), 0.004)
        seed = int(abs(price) * 1000) + horizon * 7919
        rng = np.random.default_rng(seed)
        paths = np.exp(np.cumsum(rng.normal(drift, volatility, (1200, horizon)), axis=1)) * price
        median = np.median(paths, axis=0)
        low = np.quantile(paths, 0.10, axis=0)
        high = np.quantile(paths, 0.90, axis=0)
        confidence = float(np.clip(1 - volatility * 8, 0.35, 0.95))
        start = pd.Timestamp(frame.index[-1])
        forecast = [
            ForecastPoint(
                date=(start + timedelta(days=i + 1)).date().isoformat(),
                expected=round(float(median[i]), 4),
                lower=round(float(low[i]), 4),
                upper=round(float(high[i]), 4),
            )
            for i in range(horizon)
        ]
        expected = float(median[-1])
        return QuantumResult(
            asset=asset.upper(),
            current_price=round(price, 4),
            expected_price=round(expected, 4),
            expected_return=round(expected / price - 1, 6),
            confidence=round(confidence, 4),
            forecast=forecast,
        )
