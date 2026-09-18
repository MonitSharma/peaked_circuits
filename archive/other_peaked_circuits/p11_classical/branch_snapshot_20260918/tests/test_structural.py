from __future__ import annotations
# ruff: noqa: E402, I001

import numpy as np
import pytest

qiskit = pytest.importorskip("qiskit")
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from compiler.normalization import normalize_exact

from structural.dynamic_permutation import track
from structural.matching import hungarian
from structural.patch_unitary import patch_unitary, phase_insensitive_fidelity
from structural.qasm_events import Event, parse_qasm
from structural.sequence_matching import edge_agreement, sequence_assignment
from structural.simplify import cancel_adjacent_inverses
from structural.sparse_state import TopKSparseState
from structural.unitary_matching import layer_unitary_compatibility, unitary_assignment
from structural.unitary_sequence import dtw_similarity


def test_qasm_extraction_and_layering():
    circuit = parse_qasm("circuits/fixtures/small_random.qasm")
    assert circuit.n_qubits == 3
    assert circuit.n_two_qubit > 0
    assert all(event.q2_index is not None for event in circuit.two_qubit)
    assert [event.q2_index for event in circuit.two_qubit] == list(range(circuit.n_two_qubit))


def test_hungarian_recovers_synthetic_hidden_permutation():
    rng = np.random.default_rng(4)
    features = np.eye(12)
    permutation = rng.permutation(12)
    matrix = features @ features[permutation].T
    assignment = hungarian(matrix)
    assert assignment.permutation == tuple(int(value) for value in np.argsort(permutation))


def test_dynamic_tracker_prefers_coherent_permutations():
    identity = np.eye(5)
    swapped = identity[[1, 0, 2, 3, 4]]
    path = track([identity, swapped, swapped], beam_width=8, transition_penalty=0.2)
    assert len(path) == 3
    assert path[-1].permutation == (1, 0, 2, 3, 4)


def test_patch_equivalence_is_phase_insensitive():
    circuit = parse_qasm("circuits/fixtures/small_random.qasm")
    events = tuple(event for event in circuit.events if len(event.wires) == 2)[:1]
    unitary = patch_unitary(events, events[0].wires)
    assert np.isclose(phase_insensitive_fidelity(unitary, np.exp(0.4j) * unitary), 1.0)


def test_exact_inverse_cancellation():
    circuit = parse_qasm("circuits/fixtures/small_random.qasm")
    event = next(event for event in circuit.events if event.gate == "cz")
    kept, cancellations = cancel_adjacent_inverses([event, event])
    assert kept == []
    assert cancellations[0]["type"] == "exact_inverse"


def test_layer_unitary_matching_has_identity_signal_on_identical_layers():
    circuit = parse_qasm("circuits/fixtures/small_random.qasm")
    score, overlap = layer_unitary_compatibility(circuit, [0], [0])
    assert score[0, 0] > 0.99
    assert overlap[0, 0] == 1
    permutation, _, _ = unitary_assignment(score, overlap)
    assert permutation[0] == 0


def test_sequence_matching_recovers_synthetic_hidden_permutation():
    rng = np.random.default_rng(17)
    n_qubits = 8
    left = rng.integers(0, n_qubits, size=(240, 2))
    left = left[left[:, 0] != left[:, 1]][:180]
    hidden = rng.permutation(n_qubits)
    right = hidden[left][:, ::-1]
    result = sequence_assignment(left, right, n_qubits=n_qubits, seed=5, restarts=16)
    assert edge_agreement(left, right, np.asarray(result.permutation)) == 1.0
    assert result.permutation == tuple(int(value) for value in hidden)


def test_topk_sparse_state_is_exact_when_support_budget_is_sufficient():
    state = TopKSparseState(2, retained=4)
    state.apply(Event(0, "u", (0,), (np.pi, 0.0, 0.0), 0, None, 1))
    state.apply(Event(1, "u", (1,), (np.pi, 0.0, 0.0), 0, None, 2))
    assert np.isclose(state.probability(3), 1.0)
    assert np.isclose(np.sum(np.abs(state.amplitudes) ** 2), 1.0)


def test_unitary_sequence_alignment_recovers_identical_reversed_sequence():
    rng = np.random.default_rng(22)
    left = [np.linalg.qr(rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2)))[0] for _ in range(5)]
    right = [matrix.conj().T for matrix in left]
    assert np.isclose(dtw_similarity(left, right, adjoint_left=True), 1.0)


def test_exact_normalization_preserves_small_circuit_unitary():
    circuit = QuantumCircuit.from_qasm_file("circuits/fixtures/small_random.qasm")
    result = normalize_exact(circuit)
    assert np.allclose(Operator(circuit).data, Operator(result.circuit).data, atol=1e-12)
    assert result.after.two_qubit_gates == result.before.two_qubit_gates


def test_parse_u3_iswap_and_named_registers():
    """P5/P6/P8 use `u3`, `iswap`, and non-`q` register names.

    Before this was supported, `parse_qasm` raised on the first gate line of
    P6 and P8, so no structural analysis could run on them at all.
    """
    import numpy as np
    from pathlib import Path
    from structural.qasm_events import parse_qasm
    from structural.patch_unitary import gate_matrix, Event

    root = Path(__file__).resolve().parents[1]
    inputs = root / "results/expert_review_p5_p6_p8_20260828/inputs"
    cases = [
        (inputs / "P5_granite_summit.qasm", 44, 1892),   # register named q83
        (inputs / "P6_titan_pinnacle.qasm", 62, 3494),   # u3 + cz
        (inputs / "P8_grid_888_iswap.qasm", 40, 888),    # u3 + iswap + gate decl
        (root / "data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm", 56, 1917),
    ]
    for path, n_qubits, n_two_qubit in cases:
        if not path.is_file():
            continue
        circuit = parse_qasm(path)
        assert circuit.n_qubits == n_qubits, path.name
        assert circuit.n_two_qubit == n_two_qubit, path.name

    # u3 is normalised to u, so its matrix is the standard 3-parameter rotation
    u3 = gate_matrix(Event(0, "u", (0,), (0.7, 1.1, -0.4), 0, None, 1))
    assert np.allclose(u3.conj().T @ u3, np.eye(2), atol=1e-12)

    iswap = gate_matrix(Event(0, "iswap", (0, 1), (), 0, None, 1))
    assert np.allclose(iswap.conj().T @ iswap, np.eye(4), atol=1e-12)
    assert np.allclose(iswap, np.array([[1, 0, 0, 0], [0, 0, 1j, 0],
                                        [0, 1j, 0, 0], [0, 0, 0, 1]]))
