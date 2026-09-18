"""Canonical Qiskit-to-sparse-simulator gate stream.

Qiskit is the source of truth for instruction matrices.  The stream stores
matrices in Qiskit's local convention (the first qarg is the local
least-significant bit for ``Statevector.evolve``). The adapters explicitly
convert the two-qubit matrix for BASS, whose kernel indexes the first qarg as
the local most-significant bit. qstvec accepts the Qiskit convention directly.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator


@dataclass(frozen=True)
class ParsedGate:
    name: str
    qubits: tuple[int, ...]
    matrix: np.ndarray
    original_params: tuple[float, ...]
    instruction_index: int

    @property
    def n_qubits(self) -> int:
        return len(self.qubits)

    def qstvec_matrix(self) -> np.ndarray:
        """Return this gate in qstvec/Qiskit local little-endian convention."""
        return self.matrix

    def bass_matrix(self) -> np.ndarray:
        """Return this gate in BASS's ``(b_first << 1) | b_second`` convention."""
        if self.n_qubits == 1:
            return self.matrix
        if self.n_qubits == 2:
            permutation = [0, 2, 1, 3]
            return self.matrix[np.ix_(permutation, permutation)]
        raise ValueError("only one- and two-qubit gates are supported")


@dataclass(frozen=True)
class CircuitStream:
    n_qubits: int
    gates: tuple[ParsedGate, ...]
    measurement_permutation: tuple[int, ...]
    qasm_sha256: str | None
    canonical_sha256: str


def _real_params(operation) -> tuple[float, ...]:
    values = []
    for value in operation.params:
        try:
            values.append(float(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"non-numeric gate parameter: {value!r}") from exc
    return tuple(values)


def _canonical_payload(n_qubits: int, gates: Iterable[ParsedGate], permutation):
    return {
        "n_qubits": n_qubits,
        "measurement_permutation": list(permutation),
        "gates": [
            {
                "name": gate.name,
                "qubits": list(gate.qubits),
                "original_params": list(gate.original_params),
                "instruction_index": gate.instruction_index,
                "matrix": [
                    [[float(value.real), float(value.imag)] for value in row]
                    for row in gate.matrix
                ],
            }
            for gate in gates
        ],
    }


def stream_from_circuit(circuit: QuantumCircuit, *, qasm_sha256: str | None = None) -> CircuitStream:
    gates: list[ParsedGate] = []
    measured: list[tuple[int, int]] = []
    for instruction_index, item in enumerate(circuit.data):
        operation = item.operation
        name = operation.name.lower()
        qubits = tuple(circuit.find_bit(qbit).index for qbit in item.qubits)
        if name == "measure":
            if len(item.clbits) != 1:
                raise ValueError("only single-bit measurements are supported")
            measured.append((circuit.find_bit(item.clbits[0]).index, qubits[0]))
            continue
        if name in {"barrier", "delay"}:
            continue
        if len(qubits) not in {1, 2}:
            raise ValueError(f"unsupported {len(qubits)}-qubit instruction {name}")
        matrix = np.asarray(Operator(operation).data, dtype=np.complex128)
        expected = 2 ** len(qubits)
        if matrix.shape != (expected, expected):
            raise ValueError(f"unexpected matrix shape for {name}: {matrix.shape}")
        gates.append(
            ParsedGate(
                name=name,
                qubits=qubits,
                matrix=matrix,
                original_params=_real_params(operation),
                instruction_index=instruction_index,
            )
        )

    # QASM output order is classical-bit order mapped to measured qubits.  If
    # no measurements are present, logical output order is the circuit order.
    if measured:
        by_clbit = dict(measured)
        if set(by_clbit) != set(range(len(measured))):
            raise ValueError("measurement classical bits must be contiguous")
        permutation = tuple(by_clbit[index] for index in range(len(measured)))
    else:
        permutation = tuple(range(circuit.num_qubits))
    payload = _canonical_payload(circuit.num_qubits, gates, permutation)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return CircuitStream(
        n_qubits=circuit.num_qubits,
        gates=tuple(gates),
        measurement_permutation=permutation,
        qasm_sha256=qasm_sha256,
        canonical_sha256=hashlib.sha256(encoded).hexdigest(),
    )


def parse_qasm(path: str | Path) -> CircuitStream:
    path = Path(path)
    circuit = QuantumCircuit.from_qasm_file(str(path))
    return stream_from_circuit(circuit, qasm_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
