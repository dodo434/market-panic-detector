from __future__ import annotations

import numpy as np
import pandas as pd

from backend.core.data import returns
from backend.core.schemas import ExtremeEventResult


class ExtremeEventDetector:
    """Tail-risk detector based on the external project's lagged features."""

    def detect(self, asset: str, frame: pd.DataFrame, timeframe: str = "1d") -> ExtremeEventResult:
        ret = returns(frame)
        recent = ret.tail(60)
        last = float(ret.iloc[-1])
        volatility = float(recent.std(ddof=0))
        mean = float(recent.mean())
        z = abs(last - mean) / max(volatility, 1e-6)
        drawdown = float(frame["close"].iloc[-1] / frame["close"].tail(60).max() - 1)
        probability = float(np.clip(0.02 + 0.11 * max(z - 1, 0) + 0.35 * max(-drawdown, 0), 0, 0.99))
        regime = "stress" if probability >= 0.35 else "elevated" if probability >= 0.15 else "normal"
        threshold = float(recent.quantile(0.01))
        return ExtremeEventResult(
            asset=asset.upper(),
            risk_probability=round(probability, 4),
            regime=regime,
            anomaly=bool(last <= threshold or z >= 3),
            threshold=round(threshold, 6),
            features={
                "return_zscore": round(z, 4),
                "volatility_60": round(volatility, 6),
                "drawdown_60": round(drawdown, 6),
            },
            model=f"tail-risk features ({timeframe})",
        )
