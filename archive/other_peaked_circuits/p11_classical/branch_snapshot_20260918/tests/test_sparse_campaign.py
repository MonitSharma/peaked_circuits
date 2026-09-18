import numpy as np
from qiskit import QuantumCircuit

from p12_recovery.sparse_campaign.common_metrics import (
    hamming,
    target_probability_in_product_frame,
)
from p12_recovery.sparse_campaign.qasm_adapter import stream_from_circuit


def test_qiskit_and_bass_two_qubit_conventions_are_explicit():
    qc = QuantumCircuit(2)
    qc.cx(0, 1)
    gate = stream_from_circuit(qc).gates[0]
    assert np.array_equal(gate.qstvec_matrix(), gate.matrix)
    assert np.array_equal(gate.bass_matrix(), gate.matrix[[0, 2, 1, 3]][:, [0, 2, 1, 3]])


def test_measurement_permutation_is_classical_bit_order():
    qc = QuantumCircuit(3, 3)
    qc.measure(2, 0)
    qc.measure(0, 1)
    qc.measure(1, 2)
    assert stream_from_circuit(qc).measurement_permutation == (2, 0, 1)


def test_product_frame_target_amplitude():
    class State:
        x = np.array([0, 1], dtype=np.uint64)
        alpha = np.array([1 / np.sqrt(2), 1 / np.sqrt(2)], dtype=np.complex128)
        nnz = 2

    transforms = [np.eye(2, dtype=np.complex128)]
    assert abs(target_probability_in_product_frame(State(), transforms, 1, "0") - 0.5) < 1e-12


def test_hamming_validates_lengths():
    assert hamming("0101", "0111") == 1
