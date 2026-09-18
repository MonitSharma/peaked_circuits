from p12_recovery.interaction_graph import build_interaction_graph, interaction_statistics
from p12_recovery.qasm_io import parse_qasm_text


def test_weighted_interaction_graph() -> None:
    circuit = parse_qasm_text(
        'OPENQASM 2.0; include "qelib1.inc"; qreg q[3]; cz q[0],q[1]; cz q[0],q[1]; cx q[1],q[2];'
    )
    graph = build_interaction_graph(circuit)
    stats = interaction_statistics(graph)
    assert graph[0][1]["weight"] == 2
    assert stats.number_of_edges == 2
    assert stats.fully_connected
    assert stats.diameter == 2
