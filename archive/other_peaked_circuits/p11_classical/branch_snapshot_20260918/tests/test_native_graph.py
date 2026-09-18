from __future__ import annotations

from p12_recovery.peak.native_graph import reconstruct_native_graph


def test_p8_native_graph_is_exact_and_not_false_5x8_grid():
    graph = reconstruct_native_graph(
        "results/expert_review_p5_p6_p8_20260828/inputs/P8_grid_888_iswap.qasm"
    )
    assert graph.n_qubits == 40
    assert len(graph.edges) == 63
    assert graph.iswap_count == 888
    assert not graph.exact_rectangular_grid
