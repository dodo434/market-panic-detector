"""Stable stock anchors for each mode. Local co-movement contracts each radius."""

import numpy as np
from scipy.sparse.csgraph import shortest_path
from panic_detector.networks.mst import tree_edges


def anchors(matrix: np.ndarray, cutoff: float = 0.5) -> np.ndarray:
    """Classical scaling of initial distances fixes orientation across all dates."""
    distance = np.sqrt(2 * (1 - np.clip(matrix, -1, 1)))
    n = len(matrix)
    tree = np.zeros_like(distance)
    a, b = tree_edges(matrix).T
    tree[a, b] = tree[b, a] = np.maximum(distance[a, b], 1e-9)
    modes = [
        np.where(matrix >= cutoff, distance, 2.0),
        shortest_path(tree, directed=False),
        distance,
    ]
    layouts = []
    center = np.eye(n) - np.ones((n, n)) / n
    for metric in modes:
        np.fill_diagonal(metric, 0)
        values, vectors = np.linalg.eigh(-0.5 * center @ (metric**2) @ center)
        xy = vectors[:, -2:] * np.sqrt(np.maximum(values[-2:], 0))
        # Small deterministic offsets distinguish coincident sector neighbours.
        angles = np.arange(n) * 2.399963
        xy += 0.14 * np.column_stack((np.cos(angles), np.sin(angles)))
        # A short repulsion pass separates overlapping labels in dense sectors.
        origin = xy.copy()
        for _ in range(32):
            delta = xy[:, None, :] - xy[None, :, :]
            squared = np.sum(delta**2, axis=2, keepdims=True)
            xy += 0.003 * (delta / (0.02 + squared)).sum(axis=1) + 0.045 * (origin - xy)
        xy -= xy.mean(axis=0)
        layouts.append(xy / max(np.linalg.norm(xy, axis=1).max(), 1e-8))
    return np.asarray(layouts)


def positions(base: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    affinity = (matrix.sum(axis=1) - 1) / (len(matrix) - 1)
    return base * (1 - 0.9 * np.clip(affinity, 0, 1))[None, :, None]
