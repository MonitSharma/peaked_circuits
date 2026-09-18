from pathlib import Path

from p12_recovery.peak.graph_bp import BinaryPairwiseGraph


def test_environment_factor_contract_is_positive_and_normalized() -> None:
    graph = BinaryPairwiseGraph(
        [[0.6, 0.4], [0.5, 0.5]],
        {(0, 1): [[0.4, 0.2], [0.1, 0.3]]},
    )
    result = graph.sum_product()
    assert result.converged
    assert all(abs(sum(row) - 1.0) < 1e-12 for row in result.beliefs)


def test_target_environment_script_exists() -> None:
    assert Path("scripts/run_p8_graph_bp_environment.py").is_file()
