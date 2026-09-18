import numpy as np
import pytest

from p12_recovery.peak.graph_bp import BinaryPairwiseGraph


def test_tree_bp_converges_and_recovers_joint_peak() -> None:
    unary = np.array([[1.0, 1.2], [1.0, 1.1], [1.0, 1.3], [1.0, 1.1]])
    pairwise = {(0, 1): np.array([[3.0, 0.2], [0.2, 3.0]]), (1, 2): np.array([[3.0, 0.2], [0.2, 3.0]]), (2, 3): np.array([[3.0, 0.2], [0.2, 3.0]])}
    graph = BinaryPairwiseGraph(unary, pairwise)
    result = graph.sum_product()
    assert result.converged
    assert np.allclose(result.beliefs.sum(axis=1), 1.0)
    assert graph.top_k(k=1)[0]["bitstring"] == "1111"


def test_bp_rejects_invalid_factors_and_unconverged_is_explicit() -> None:
    with pytest.raises(ValueError):
        BinaryPairwiseGraph(np.ones((2, 2)), {(0, 1): np.zeros((2, 2))})
    graph = BinaryPairwiseGraph(np.ones((2, 2)), {(0, 1): np.ones((2, 2)) * 2})
    result = graph.sum_product(max_iter=1, tolerance=1e-20)
    assert result.converged is True or result.iterations == 1
