from pathlib import Path

from p12_recovery.circuit_inspection import inspect_circuit


def test_fixture_gate_arity_depth_and_unused(root: Path, tmp_path: Path) -> None:
    qasm = tmp_path / "unused.qasm"
    qasm.write_text('OPENQASM 2.0; include "qelib1.inc"; qreg q[3]; h q[0]; cz q[0],q[1];')
    report, _ = inspect_circuit(qasm)
    assert report.gates.one_qubit_gates == 1
    assert report.gates.two_qubit_gates == 1
    assert report.gates.circuit_depth == 2
    assert report.gates.two_qubit_depth == 1
    assert report.unused_qubits == [2]
