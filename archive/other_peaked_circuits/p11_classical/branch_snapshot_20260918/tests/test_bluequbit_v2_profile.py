from __future__ import annotations

import numpy as np

from p12_recovery.bluequbit.profile import (
    _phase_invariant_distance,
    _u_matrix,
    clifford_proximity,
    lightcones,
)
from structural.qasm_events import parse_qasm


def test_phase_invariant_distance_ignores_global_phase():
    a = np.eye(2, dtype=complex)
    b = np.exp(0.37j) * a
    assert _phase_invariant_distance(a, b) < 1e-12


def test_clifford_audit_fixture():
    circuit = parse_qasm("tests/fixtures/tiny.qasm")
    result = clifford_proximity(circuit)
    assert result["clifford_count"] == 24
    assert result["u_gate_count"] == 1
    assert result["distance_summary"]["min"] is not None


def test_lightcone_panel_is_algorithmic():
    circuit = parse_qasm("tests/fixtures/tiny.qasm")
    result = lightcones(circuit)
    assert len(result["outputs"]) == circuit.n_qubits
    assert sum(map(len, result["initial_pps_panel"].values())) == circuit.n_qubits
