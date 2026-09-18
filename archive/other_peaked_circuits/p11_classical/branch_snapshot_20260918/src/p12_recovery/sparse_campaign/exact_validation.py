"""Dense small-circuit validation for the three sparse adapters."""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from .common_metrics import bitstring, hamming
from .qasm_adapter import CircuitStream, stream_from_circuit


@dataclass(frozen=True)
class ValidationResult:
    name: str
    qasm_n_qubits: int
    gate_count: int
    qstvec_fidelity: float
    bass_fixed_fidelity: float
    bass_adaptive_fidelity: float
    qstvec_max_amplitude_error: float
    bass_fixed_max_amplitude_error: float
    bass_adaptive_max_amplitude_error: float
    qstvec_top1: str
    bass_fixed_top1: str
    bass_adaptive_top1: str
    exact_top1: str
    measurement_permutation: tuple[int, ...]


def _dense_from_qstvec(sv, n: int) -> np.ndarray:
    dense = np.zeros(2**n, dtype=np.complex128)
    for index, amplitude in zip(sv.basis, sv.alpha):
        dense[int(index)] = amplitude
    return dense


def _dense_from_bass(simulator, state) -> np.ndarray:
    if hasattr(simulator, "to_statevector"):
        return np.asarray(simulator.to_statevector(state), dtype=np.complex128)
    dense = np.zeros(2 ** simulator.N, dtype=np.complex128)
    dense[state.x[: state.nnz].astype(int)] = state.alpha[: state.nnz]
    return dense


def _fidelity(left: np.ndarray, right: np.ndarray) -> float:
    left = left / np.linalg.norm(left)
    right = right / np.linalg.norm(right)
    return float(abs(np.vdot(left, right)) ** 2)


def validate_circuit(name: str, circuit: QuantumCircuit, qstvec_cls, fixed_cls, bass_cls) -> ValidationResult:
    stream = stream_from_circuit(circuit)
    exact = Statevector.from_int(0, dims=2**stream.n_qubits)
    for item in circuit.data:
        if item.operation.name.lower() not in {"measure", "barrier", "delay"}:
            exact = exact.evolve(item.operation, [circuit.find_bit(q).index for q in item.qubits])
    exact_dense = np.asarray(exact.data, dtype=np.complex128)
    exact_top1 = bitstring(int(np.argmax(abs(exact_dense) ** 2)), stream.n_qubits)

    qsv = qstvec_cls(stream.n_qubits)
    for gate in stream.gates:
        qsv.evolve(gate.qstvec_matrix(), gate.qubits)
    q_dense = _dense_from_qstvec(qsv, stream.n_qubits)

    fixed = fixed_cls(stream.n_qubits, 2 ** stream.n_qubits, verbose=False)
    bass_gates = [
        type(gate)(
            gate.name,
            gate.qubits,
            gate.bass_matrix(),
            gate.original_params,
            gate.instruction_index,
        )
        for gate in stream.gates
    ]
    fixed_state = fixed.simulate(bass_gates, seed=7)
    fixed_dense = _dense_from_bass(fixed, fixed_state)

    adaptive = bass_cls(
        stream.n_qubits,
        2 ** stream.n_qubits,
        optimize_every=0,
        truncate_every=1,
        use_2qubit_rotations=False,
        verbose=False,
    )
    adaptive_state = adaptive.simulate(bass_gates)
    adaptive_dense = _dense_from_bass(adaptive, adaptive_state)

    def max_error(value):
        return float(np.max(np.abs(value - exact_dense)))

    return ValidationResult(
        name=name,
        qasm_n_qubits=stream.n_qubits,
        gate_count=len(stream.gates),
        qstvec_fidelity=_fidelity(q_dense, exact_dense),
        bass_fixed_fidelity=_fidelity(fixed_dense, exact_dense),
        bass_adaptive_fidelity=_fidelity(adaptive_dense, exact_dense),
        qstvec_max_amplitude_error=max_error(q_dense),
        bass_fixed_max_amplitude_error=max_error(fixed_dense),
        bass_adaptive_max_amplitude_error=max_error(adaptive_dense),
        qstvec_top1=bitstring(int(np.argmax(abs(q_dense) ** 2)), stream.n_qubits),
        bass_fixed_top1=bitstring(int(np.argmax(abs(fixed_dense) ** 2)), stream.n_qubits),
        bass_adaptive_top1=bitstring(int(np.argmax(abs(adaptive_dense) ** 2)), stream.n_qubits),
        exact_top1=exact_top1,
        measurement_permutation=stream.measurement_permutation,
    )


def representative_panel():
    panel = []
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.x(1)
    qc.rz(0.37, 2)
    panel.append(("one_qubit", qc))

    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 2)
    qc.cz(2, 1)
    panel.append(("nonadjacent_two_qubit", qc))

    qc = QuantumCircuit(3)
    qc.u(0.31, -0.22, 0.77, 1)
    qc.rzz(0.41, 2, 0)
    qc.swap(1, 2)
    panel.append(("arbitrary_and_rzz", qc))

    qc = QuantumCircuit(3, 3)
    qc.h(0)
    qc.cx(0, 2)
    qc.measure(2, 0)
    qc.measure(0, 1)
    qc.measure(1, 2)
    panel.append(("measurement_permutation", qc))
    return panel


def run_panel() -> list[dict]:
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "external/qstvec/src"))
    sys.path.insert(0, str(root / "external/bass"))
    from qstvec import Statevector as QStatevector
    from src.simulation.bass_simulator import BASS
    from src.simulation.simulator import FixedBasisSimulator

    results = []
    for name, circuit in representative_panel():
        result = validate_circuit(name, circuit, QStatevector, FixedBasisSimulator, BASS)
        if min(result.qstvec_fidelity, result.bass_fixed_fidelity, result.bass_adaptive_fidelity) < 1 - 1e-10:
            raise AssertionError(result)
        results.append(asdict(result))
    return results
