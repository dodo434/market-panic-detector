import numpy as np
import pandas as pd

from panic_detector.features.rolling_corr import average_correlation, correlation_matrix
from panic_detector.models.eigen import top_eigenvalue
from panic_detector.models.panic_score import classify_status
from panic_detector.models.random_matrix import marchenko_pastur_upper_bound


def test_correlation_matrix_is_symmetric_unit_diagonal():
    rng = np.random.default_rng(42)
    returns = rng.normal(size=(200, 8))
    matrix = correlation_matrix(pd.DataFrame(returns, columns=[f"S{i}" for i in range(8)]))
    values = matrix.to_numpy()
    assert np.allclose(values, values.T)
    assert np.allclose(np.diag(values), 1.0)


def test_top_eigenvalue_equicorrelation():
    n = 10
    rho = 0.35
    matrix = np.full((n, n), rho)
    np.fill_diagonal(matrix, 1.0)
    assert np.isclose(top_eigenvalue(matrix), 1.0 + (n - 1) * rho)


def test_average_correlation():
    n = 4
    rho = 0.25
    matrix = np.full((n, n), rho)
    np.fill_diagonal(matrix, 1.0)
    assert np.isclose(average_correlation(matrix), rho)


def test_marchenko_pastur_bound():
    n = 100
    window = 60
    expected = (1.0 + np.sqrt(n / window)) ** 2
    assert np.isclose(marchenko_pastur_upper_bound(n, window), expected)


def test_status_thresholds():
    assert classify_status(49.99) == "CALM"
    assert classify_status(50) == classify_status(80) == "NERVOUS"
    assert classify_status(80.001) == "PANIC"
