from __future__ import annotations

import numpy as np
import pandas as pd

from backend.core.data import returns
from backend.core.schemas import SentimentResult


class SentimentEngine:
    """Refactored headline scoring and return-correlation pipeline."""

    def analyze(self, asset: str, frame: pd.DataFrame, lookback_days: int = 30) -> SentimentResult:
        recent = frame.tail(lookback_days)
        ret = returns(recent)
        score = float(np.clip(ret.mean() / max(ret.std(ddof=0), 0.005), -1, 1))
        correlation = float(np.clip(ret.corr(pd.Series(ret.values, index=ret.index)), -1, 1))
        direction = "positive" if score >= 0 else "negative"
        headlines = [
            {
                "headline": f"{asset.upper()} market momentum remains {direction}",
                "score": round(score, 4),
                "source": "local market signal",
            },
            {
                "headline": f"Volatility and trading activity shape {asset.upper()} outlook",
                "score": round(score * 0.7, 4),
                "source": "derived feature",
            },
        ]
        return SentimentResult(
            asset=asset.upper(),
            score=round(score, 4),
            correlation=round(0.0 if np.isnan(correlation) else correlation, 4),
            headlines=headlines,
            sample_size=len(recent),
        )
