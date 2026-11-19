"""Unit tests for ticker validation."""

from __future__ import annotations

import pytest

from panic_detector.data.alpaca_client import validate_tickers


def test_validate_tickers_normalizes_and_deduplicates() -> None:
    assert validate_tickers([" aapl ", "MSFT", "aapl"]) == ["AAPL", "MSFT"]


@pytest.mark.parametrize("ticker", ["", "AAPL;rm", "../AAPL", "AAPL1" * 20])
def test_validate_tickers_rejects_unsafe_input(ticker: str) -> None:
    with pytest.raises(ValueError):
        validate_tickers([ticker])


def test_validate_tickers_rejects_empty_and_too_many() -> None:
    with pytest.raises(ValueError):
        validate_tickers([])
    with pytest.raises(ValueError):
        validate_tickers([f"S{index}" for index in range(51)])
