from pathlib import Path

from scripts.analyze_bluequbit_p1 import _cut_rows, _graph_metrics, _ordering_rows
from structural.qasm_events import parse_qasm


FIXTURE = Path(__file__).parents[1] / "circuits/fixtures/small_random.qasm"


def test_graph_metrics_separates_simple_and_weighted_degree():
    circuit = parse_qasm(FIXTURE)
    metrics = _graph_metrics(circuit)
    assert metrics["max_degree"] <= circuit.n_qubits - 1
    assert metrics["total_two_qubit_interaction_count"] == circuit.n_two_qubit
    assert metrics["mean_weighted_degree"] >= metrics["mean_degree"]


def test_cut_scan_has_explicit_ratio_and_index():
    rows = _cut_rows(parse_qasm(FIXTURE), [0.5])
    assert rows[0]["ratio"] == 0.5
    assert rows[0]["cut_q2_index"] == 1


def test_structural_ordering_proxies_include_spectral_and_rcm():
    names = {row["ordering"] for row in _ordering_rows(parse_qasm(FIXTURE))}
    assert {"fiedler", "rcm"}.issubset(names)
