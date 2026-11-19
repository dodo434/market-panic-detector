from itertools import islice
import numpy as np
import pandas as pd
import pytest
from panic_detector.analysis import analyze
from panic_detector.data.cleaning import clean_prices
from panic_detector.features.returns import daily_log_returns
from panic_detector.features.rolling_corr import correlation_matrix, windows
from panic_detector.models.panic_score import historical_levels
from panic_detector.models.random_matrix import marchenko_pastur_upper_bound
from panic_detector.networks.mst import tree_edges
from panic_detector.networks.threshold import threshold_edges
from panic_detector.networks.weighted import all_pairs
from panic_detector.viz.plots import scene


def test_historical_rank_is_prefix_stable_and_respects_ties():
    shares = [0.2, 0.2, 0.6, 0.1, 0.2]
    assert historical_levels(shares).tolist() == [50, 50, 100, 0, 50]
    np.testing.assert_equal(historical_levels(shares)[:3], historical_levels(shares[:3]))


def test_small_gaps_and_outages():
    days = pd.bdate_range("2022-01-03", periods=20)
    prices = pd.DataFrame(
        {"A": np.arange(20, dtype=float) + 8, "B": np.arange(20) + 12, "C": np.nan}, index=days
    )
    prices.iloc[3:8, 0] = np.nan
    clean, dropped = clean_prices(prices)
    assert dropped == ["C"]
    assert clean.iloc[3:6, 0].eq(10).all()
    assert clean.iloc[6:8, 0].isna().all()
    sample = prices["B"].iloc[[0, 1, -1]].to_frame()
    result = daily_log_returns(sample)
    assert np.isclose(result.iloc[0, 0], np.log(13 / 12))
    assert np.isnan(result.iloc[-1, 0])


def test_complete_varying_windows_only():
    dates = pd.bdate_range("2022-01-03", periods=7)
    returns = pd.DataFrame(
        {"A": [1, 1, 1, 2, np.nan, 3, 4], "B": [2, 3, 1, 5, 4, 3, 2]}, index=dates
    )
    samples = list(windows(returns, 3))
    assert len(samples) == 1 and samples[0][0] == dates[3]
    np.testing.assert_allclose(samples[0][1], correlation_matrix(returns.iloc[1:4]))
    with pytest.raises(ValueError):
        correlation_matrix(returns)
    with pytest.raises(ValueError):
        list(islice(windows(returns, 1), 1))
    with pytest.raises(ValueError):
        marchenko_pastur_upper_bound(0, 60)


def test_graph_weights_ties_and_distance_tree():
    m = np.array([[1, 1, 0.5], [1, 1, -0.1], [0.5, -0.1, 1.0]])
    pairs = all_pairs(3)
    assert pairs.shape == (3, 2)
    np.testing.assert_equal(threshold_edges(m, pairs, 0.5), [[0, 1], [0, 2]])
    assert set(map(tuple, tree_edges(m))) == {(0, 1), (0, 2)}


def test_stronger_common_factor_and_all_scene_modes():
    rng = np.random.default_rng(42)
    moves = rng.normal(size=(110, 5))
    moves[60:] += 8 * rng.normal(size=(50, 1))
    prices = pd.DataFrame(
        np.exp(0.01 * moves.cumsum(axis=0)),
        index=pd.bdate_range("2022-01-03", periods=110),
        columns=list("ABCDE"),
    )
    result = analyze(prices, 20)
    assert len(result) == 90
    assert result[-1]["average"] > 0.9 and result[-1]["share"] > 0.9
    np.testing.assert_allclose(result[-1]["corr"], np.corrcoef(moves[-20:].T), rtol=1e-6)
    for mode in range(3):
        view = scene(result, mode, 0.5)
        assert view.positions.shape == (90, 5, 2)
        assert np.isfinite(view.positions).all()
        assert len(view.lines) == 90
        if mode == 2:
            assert sum(group.shape[1] for group in view.lines[-1]) == 20
    with pytest.raises(ValueError):
        analyze(prices.iloc[:4], 20)
