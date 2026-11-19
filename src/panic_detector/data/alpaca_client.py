"""Adjusted daily IEX closes. Only this adapter depends on the market-data SDK."""

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from panic_detector.data.credentials import get_credentials
from panic_detector.data.universe import validate_tickers as validate_tickers


class MissingKeys(ValueError):
    pass


class TimedAdapter(HTTPAdapter):
    def send(self, request, **kwargs):
        kwargs["timeout"] = (5, 30)
        return super().send(request, **kwargs)


def fetch(
    tickers: Sequence[str], start: date, end: date, progress: Callable[[str], None]
) -> pd.DataFrame:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import Adjustment, DataFeed

    keys = get_credentials()
    if not all(keys):
        raise MissingKeys("Connect Alpaca to download the stock history.")
    client = StockHistoricalDataClient(*keys, url_override="https://data.alpaca.markets")
    client._retry = 0
    client._session.mount(
        "https://",
        TimedAdapter(
            max_retries=Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods={"GET"},
                respect_retry_after_header=False,
            )
        ),
    )
    frames = []
    try:
        for i in range(0, len(tickers), 10):
            group = list(tickers[i : i + 10])
            progress(f"Downloading stocks {i+1}–{i+len(group)} of {len(tickers)}…")
            req = StockBarsRequest(
                symbol_or_symbols=group,
                timeframe=TimeFrame.Day,
                start=datetime.combine(start, datetime.min.time(), tzinfo=UTC),
                end=min(
                    datetime.now(UTC),
                    datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
                ),
                feed=DataFeed.IEX,
                adjustment=Adjustment.ALL,
            )
            bars = getattr(client.get_stock_bars(req), "df")
            if not bars.empty:
                frames.append(bars["close"].unstack("symbol"))
    except Exception:
        raise ValueError("Check your Alpaca connection and retry the download.") from None
    finally:
        client._session.close()
    if not frames:
        raise ValueError("Alpaca has no prices for these symbols and dates.")
    result = pd.concat(frames, axis=1).reindex(columns=tickers).sort_index()
    result.index = pd.DatetimeIndex(result.index).tz_localize(None).normalize()
    return result
