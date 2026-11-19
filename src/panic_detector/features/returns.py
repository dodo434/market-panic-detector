"""Daily price-relative measurements."""

import numpy as np
import pandas as pd


def daily_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Log differences add across time. Preserve gaps so windows cannot bridge an outage."""
    returns = np.log(prices.where(prices > 0)).diff().replace([np.inf, -np.inf], np.nan)
    gap = prices.index.to_series().diff() > pd.Timedelta(days=7)
    returns.loc[gap] = np.nan
    return returns.iloc[1:]
