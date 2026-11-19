"""Align sessions without inventing pre-listing history or spanning long outages."""

import numpy as np
import pandas as pd


def clean_prices(
    prices: pd.DataFrame, missing_threshold: float = 0.10
) -> tuple[pd.DataFrame, list[str]]:
    frame = prices.sort_index().astype(float)
    frame.index = pd.DatetimeIndex(frame.index).tz_localize(None).normalize()
    frame = frame[~frame.index.duplicated(keep="last")]
    frame = frame.where(np.isfinite(frame) & (frame > 0)).dropna(how="all")
    groups = frame.index.to_series().diff().dt.days.gt(7).cumsum()
    frame = frame.groupby(groups).ffill(limit=3)
    keep = (frame.isna().mean() <= missing_threshold) & (frame.nunique() > 1)
    return frame.loc[:, keep], list(frame.columns[~keep])
