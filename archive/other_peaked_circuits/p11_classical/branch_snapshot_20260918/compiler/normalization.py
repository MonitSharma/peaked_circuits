"""Deterministic exact-mode algebraic normalization for supported QASM gates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from qiskit import QuantumCircuit
from qiskit.circuit.library import CZGate
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import (
    CommutativeCancellation,
    InverseCancellation,
    Optimize1qGatesDecomposition,
    RemoveIdentityEquivalent,
)


@dataclass(frozen=True)
class CircuitMetrics:
    total_gates: int
    one_qubit_gates: int
    two_qubit_gates: int
    depth: int
    operation_counts: dict[str, int]


@dataclass(frozen=True)
class NormalizationResult:
    circuit: QuantumCircuit
    before: CircuitMetrics
    after: CircuitMetrics
    passes: tuple[str, ...]


def metrics(circuit: QuantumCircuit) -> CircuitMetrics:
    counts = Counter(str(instruction.operation.name) for instruction in circuit.data)
    one = sum(instruction.operation.num_qubits == 1 for instruction in circuit.data)
    two = sum(instruction.operation.num_qubits == 2 for instruction in circuit.data)
    return CircuitMetrics(len(circuit.data), one, two, circuit.depth(), dict(sorted(counts.items())))


def normalize_exact(circuit: QuantumCircuit) -> NormalizationResult:
    """Apply only deterministic Qiskit exact-mode algebraic passes.

    The identity pass uses its default machine-precision criterion. No routing,
    stochastic optimization, approximate synthesis, or full-state comparison is
    performed here.
    """
    passes = (
        "Optimize1qGatesDecomposition",
        "RemoveIdentityEquivalent",
        "CommutativeCancellation",
        "InverseCancellation(CZ)",
    )
    manager = PassManager(
        [
            Optimize1qGatesDecomposition(),
            RemoveIdentityEquivalent(),
            CommutativeCancellation(),
            InverseCancellation([CZGate()]),
        ]
    )
    normalized = manager.run(circuit)
    return NormalizationResult(circuit, metrics(circuit), metrics(normalized), passes)
