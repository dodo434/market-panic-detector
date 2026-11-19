from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from panic_detector import service
from panic_detector.data import alpaca_client
from panic_detector.data.paths import selected_file
from panic_detector.data.cache import safe_cache_path


def test_refresh_offline_and_failed_replacement(tmp_path, monkeypatch):
    rng = np.random.default_rng(7)
    tickers = ["AA", "BB", "CC"]
    prices = pd.DataFrame(
        np.exp(0.02 * rng.normal(size=(70, 3)).cumsum(axis=0)),
        index=pd.bdate_range("2022-01-03", periods=70),
        columns=tickers,
    )
    prices["CC"] = np.nan
    monkeypatch.setattr(alpaca_client, "fetch", lambda *args: prices)
    first = service.snapshot(tickers, 20, True, root=tmp_path)
    assert first.dtype["symbols"].names == ("AA", "BB")
    np.testing.assert_equal(service.snapshot(tickers, 20, root=tmp_path), first)
    monkeypatch.setattr(alpaca_client, "fetch", lambda *args: prices.iloc[:3])
    with pytest.raises(ValueError):
        service.snapshot(tickers, 20, True, root=tmp_path)
    processed = next((tmp_path / "processed").glob("*.npy"))
    processed.write_bytes(b"incomplete")
    rebuilt = service.snapshot(tickers, 20, root=tmp_path)
    np.testing.assert_equal(rebuilt, first)
    other = service.snapshot(tickers, 40, root=tmp_path)
    assert len(other) == 30 and len(list((tmp_path / "processed").glob("*.npy"))) == 2
    monkeypatch.setattr(service, "prepare", lambda *args: pytest.fail("recomputed on warm cache"))
    assert len(service.snapshot(tickers, 20, root=tmp_path)) == 50


def test_reject_path_escape(tmp_path):
    with pytest.raises(ValueError):
        safe_cache_path("../x.parquet", tmp_path)
    with pytest.raises(ValueError):
        selected_file(str(tmp_path / ".." / "bad.csv"), ".csv")
    with pytest.raises(ValueError):
        selected_file(str(tmp_path / "keys.txt"), ".csv")
    assert (
        selected_file("tests/fixtures/tickers.csv", ".csv")
        == Path("tests/fixtures/tickers.csv").resolve()
    )


def test_requests_use_iex_adjustment_timeout_and_safe_errors(monkeypatch):
    from datetime import date
    from types import SimpleNamespace
    from alpaca.data.historical import StockHistoricalDataClient
    from requests import Session, Request
    from requests.adapters import HTTPAdapter

    seen = []

    def fake_get(self, req):
        seen.append(req)
        assert self._base_url == "https://data.alpaca.markets"
        assert self._session.get_adapter(self._base_url).max_retries.backoff_factor > 0
        idx = pd.MultiIndex.from_product(
            [req.symbol_or_symbols, pd.date_range("2020-03-01", periods=2, tz="UTC")],
            names=["symbol", "timestamp"],
        )
        return SimpleNamespace(df=pd.DataFrame({"close": 10.0}, index=idx))

    monkeypatch.setattr(alpaca_client, "get_credentials", lambda: ("fixture", "fixture"))
    monkeypatch.setattr(StockHistoricalDataClient, "get_stock_bars", fake_get)
    result = alpaca_client.fetch(["AA", "BB"], date(2018, 1, 1), date(2020, 3, 2), lambda _: None)
    assert result.shape == (2, 2)
    assert seen[0].feed.value == "iex" and seen[0].adjustment.value == "all"
    assert seen[0].end.date() == date(2020, 3, 3)
    calls = []
    monkeypatch.setattr(HTTPAdapter, "send", lambda self, req, **kwargs: calls.append(kwargs))
    session = Session()
    alpaca_client.TimedAdapter().send(
        session.prepare_request(Request("GET", "https://example.invalid"))
    )
    assert calls[0]["timeout"] == (5, 30)

    def fail(*args):
        raise RuntimeError("private upstream response")

    monkeypatch.setattr(StockHistoricalDataClient, "get_stock_bars", fail)
    with pytest.raises(ValueError, match="Check your Alpaca connection") as exc:
        alpaca_client.fetch(["AA"], date(2018, 1, 1), date(2020, 3, 2), lambda _: None)
    assert "private" not in str(exc.value)
    monkeypatch.setattr(alpaca_client, "get_credentials", lambda: (None, None))
    with pytest.raises(alpaca_client.MissingKeys):
        alpaca_client.fetch(["AA"], date(2018, 1, 1), date(2020, 3, 2), lambda _: None)
