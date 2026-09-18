import numpy as np

from p12_recovery.peak.graph_bp import BinaryPairwiseGraph


def test_frechet_projection_produces_positive_pair_factor() -> None:
    p0_left, p0_right, raw_p00 = 0.8, 0.7, -0.1
    lower = max(1e-12, p0_left + p0_right - 1.0 + 1e-12)
    upper = min(p0_left, p0_right) - 1e-12
    p00 = min(max(raw_p00, lower), upper)
    matrix = np.array([[p00, p0_left - p00], [p0_right - p00, 1 - p0_left - p0_right + p00]])
    assert np.all(matrix > 0)
    graph = BinaryPairwiseGraph([[p0_left, 1 - p0_left], [p0_right, 1 - p0_right]], {(0, 1): matrix})
    assert graph.sum_product().converged
