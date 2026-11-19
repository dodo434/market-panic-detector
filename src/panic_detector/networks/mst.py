"""Minimum total Mantegna distance spanning all N stocks."""

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree


def tree_edges(matrix: np.ndarray) -> np.ndarray:
    distance = np.sqrt(2 * (1 - np.clip(matrix, -1, 1)))
    # Sparse graph routines interpret exact zero as a missing link.
    distance = np.maximum(distance, np.finfo(float).eps)
    tree = minimum_spanning_tree(csr_matrix(np.triu(distance, 1))).tocoo()
    return np.column_stack((tree.row, tree.col)).astype(np.int16)
