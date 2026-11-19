"""Download, cache, and clean Alpaca daily stock bars."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import re

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "AVGO",
    "ORCL", "IBM", "JPM", "BAC", "WFC", "GS", "MS", "C", "XOM",
    "CVX", "COP", "SLB", "JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO",
    "ABT", "WMT", "COST", "HD", "MCD", "NKE", "TGT", "NEE", "DUK",
    "SO", "CAT", "BA", "HON", "GE", "UPS", "V", "MA", "LIN", "FCX",
    "RTX", "LMT", "MMM", "KO", "PEP",
]

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-Z\-.]{0,11}$")


def validate_tickers(tickers: Iterable[str]) -> list[str]:
    """Validate and normalize user-provided ticker symbols."""
    validated: list[str] = []
    for raw in tickers:
        ticker = str(raw).strip().upper()
        if not TICKER_PATTERN.fullmatch(ticker):
            raise ValueError(f"Invalid ticker symbol: {raw!r}")
        if len(validated) >= 50:
            raise ValueError("A maximum of 50 tickers is supported")
        if ticker not in validated:
            validated.append(ticker)
    if not validated:
        raise ValueError("At least one ticker is required")
    return validated


def load_alpaca_keys(api_file: str | Path = "api.txt") -> tuple[str, str]:
    """Load Alpaca credentials from environment variables or api.txt.

    Environment variables take precedence. The api.txt format is ``key=<...>``
    and ``Secret=<...>``.
    """
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    if key and secret:
        return key, secret

    values: dict[str, str] = {}
    path = Path(api_file)
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if "=" in raw_line:
                name, value = raw_line.split("=", 1)
                values[name.strip().lower()] = value.strip()
    key = key or values.get("key") or values.get("alpaca_api_key")
    secret = secret or values.get("secret") or values.get("alpaca_secret_key")
    if not key or not secret:
        raise RuntimeError(
            "Alpaca credentials missing; set ALPACA_API_KEY and "
            "ALPACA_SECRET_KEY or provide api.txt."
        )
    return key, secret


def download_alpaca_bars(
    tickers: Iterable[str],
    start: date,
    end: date,
    cache_path: str | Path = "cache/alpaca_daily.parquet",
    api_file: str | Path = "api.txt",
) -> tuple[pd.DataFrame, list[str]]:
    """Download adjusted IEX bars, cache closes, clean gaps, and report drops.

    Bars are requested with split/dividend-adjusted prices. No credentials are
    persisted to code or to the cache.
    """
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    ticker_list = [ticker.upper() for ticker in tickers]
    cache = Path(cache_path)
    cache.parent.mkdir(parents=True, exist_ok=True)

    if cache.exists():
        closes = pd.read_parquet(cache)
        if isinstance(closes.index, pd.DatetimeIndex):
            closes.index = closes.index.tz_localize(None) if closes.index.tz is not None else closes.index
        return clean_prices(closes)

    key, secret = load_alpaca_keys(api_file)
    client = StockHistoricalDataClient(key, secret)
    request = StockBarsRequest(
        symbol_or_symbols=ticker_list,
        timeframe=TimeFrame.Day,
        start=datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
        end=datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc),
        adjustment=Adjustment.ALL,
        feed=DataFeed.IEX,
    )
    bars = client.get_stock_bars(request)
    frame = bars.df
    if frame is None or frame.empty:
        raise RuntimeError("Alpaca returned no bars for the requested tickers.")

    if isinstance(frame.index, pd.MultiIndex):
        close = frame["close"].unstack("symbol").sort_index()
    else:
        symbol = getattr(frame.attrs, "symbol", None)
        close = frame[["close"]].rename(columns={"close": symbol or "UNKNOWN"})
    close.index = pd.to_datetime(close.index)
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)
    close.index = close.index.normalize()
    close = close.reindex(columns=ticker_list).sort_index()
    close.to_parquet(cache)
    return clean_prices(close)


def clean_prices(prices: pd.DataFrame, missing_threshold: float = 0.10) -> tuple[pd.DataFrame, list[str]]:
    """Align prices, forward-fill gaps of at most three days, and drop sparse tickers."""
    aligned = prices.sort_index().ffill(limit=3).dropna(how="all")
    missing_fraction = aligned.isna().mean()
    keep = missing_fraction <= missing_threshold
    dropped = sorted(missing_fraction.index[~keep].tolist())
    cleaned = aligned.loc[:, keep].ffill(limit=3).dropna(how="all")
    cleaned = cleaned.loc[:, cleaned.isna().mean() <= missing_threshold]
    cleaned.index = pd.DatetimeIndex(cleaned.index).normalize()
    return cleaned, dropped


def compute_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute daily log returns and remove the initial missing row."""
    returns = pd.DataFrame(
        __import__("numpy").log(prices).diff(),
        index=prices.index,
        columns=prices.columns,
    )
    return returns.replace([float("inf"), float("-inf")], pd.NA).dropna(how="all")
