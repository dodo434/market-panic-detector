"""Correlation network construction and fixed-position layout."""

from __future__ import annotations

from typing import Literal

import networkx as nx
import numpy as np
import pandas as pd

SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Communication",
    "GOOG": "Communication", "AMZN": "Consumer Discretionary", "META": "Communication",
    "NVDA": "Technology", "AVGO": "Technology", "ORCL": "Technology", "IBM": "Technology",
    "JPM": "Financials", "BAC": "Financials", "WFC": "Financials", "GS": "Financials",
    "MS": "Financials", "C": "Financials", "V": "Financials", "MA": "Financials",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    "JNJ": "Health Care", "UNH": "Health Care", "PFE": "Health Care",
    "ABBV": "Health Care", "MRK": "Health Care", "TMO": "Health Care", "ABT": "Health Care",
    "WMT": "Consumer Staples", "COST": "Consumer Staples", "TGT": "Consumer Staples",
    "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "HD": "Consumer Discretionary", "MCD": "Consumer Discretionary", "NKE": "Consumer Discretionary",
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities",
    "CAT": "Industrials", "BA": "Industrials", "HON": "Industrials", "GE": "Industrials",
    "UPS": "Industrials", "RTX": "Industrials", "LMT": "Industrials",
    "LIN": "Materials", "FCX": "Materials", "MMM": "Industrials",
}

SECTOR_COLORS = {
    "Technology": "#4C78A8", "Communication": "#F58518",
    "Consumer Discretionary": "#E45756", "Financials": "#54A24B",
    "Energy": "#B279A2", "Health Care": "#72B7B2", "Consumer Staples": "#EECA3B",
    "Utilities": "#BAB0AC", "Industrials": "#FF9DA6", "Materials": "#9D755D",
}


def build_network(
    corr: pd.DataFrame,
    kind: Literal["threshold", "mst", "weighted"] = "threshold",
    threshold: float = 0.5,
) -> nx.Graph:
    """Build threshold, minimum-spanning-tree, or fully weighted graph."""
    graph = nx.Graph()
    graph.add_nodes_from(corr.columns)
    values = corr.to_numpy(dtype=float)
    tickers = list(corr.columns)
    if kind == "threshold":
        for i, left in enumerate(tickers):
            for j in range(i + 1, len(tickers)):
                right = tickers[j]
                rho = float(values[i, j])
                if rho > threshold:
                    graph.add_edge(left, right, weight=rho)
    elif kind == "mst":
        full = nx.Graph()
        for i, left in enumerate(tickers):
            for j in range(i + 1, len(tickers)):
                right = tickers[j]
                rho = float(np.clip(values[i, j], -1.0, 1.0))
                distance = np.sqrt(max(0.0, 2.0 * (1.0 - rho)))
                full.add_edge(left, right, weight=distance)
        graph = nx.minimum_spanning_tree(full, weight="weight")
    elif kind == "weighted":
        for i, left in enumerate(tickers):
            for j in range(i + 1, len(tickers)):
                right = tickers[j]
                rho = float(values[i, j])
                graph.add_edge(left, right, weight=rho)
    else:
        raise ValueError(f"Unknown network kind: {kind}")
    return graph


def fixed_layout(reference_corr: pd.DataFrame, seed: int = 42) -> dict[str, tuple[float, float]]:
    """Create a seeded spring layout used for every animation frame."""
    graph = build_network(reference_corr, kind="weighted")
    return nx.spring_layout(graph, seed=seed, weight="weight", k=0.55)
