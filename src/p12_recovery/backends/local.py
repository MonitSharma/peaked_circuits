from __future__ import annotations

from typing import Any

from p12_recovery.models import BackendDescriptor, CompilationConfig, CostEstimate, ValidationResult


class LocalBackend:
    def describe(self) -> BackendDescriptor:
        return BackendDescriptor(
            provider="local", device_name="pytket-local-passes", target_type="local"
        )

    def compile(self, circuit: Any, config: CompilationConfig) -> Any:
        del config
        try:
            from pytket.passes import DecomposeBoxes, RemoveRedundancies
        except ImportError as exc:
            raise RuntimeError("pytket is required for local compilation") from exc
        compiled = circuit.copy()
        DecomposeBoxes().apply(compiled)
        RemoveRedundancies().apply(compiled)
        return compiled

    def validate(self, circuit: Any) -> ValidationResult:
        return ValidationResult(
            passed=bool(circuit.n_qubits and circuit.n_gates),
            predicates={"nonempty": bool(circuit.n_gates), "has_qubits": bool(circuit.n_qubits)},
        )

    def estimate_cost(self, circuit: Any, shots: int) -> CostEstimate | None:
        del circuit
        return CostEstimate(shots=shots, notes=["Local execution consumes no HQCs"])

    def submit(self, circuit: Any, shots: int) -> Any:
        del circuit, shots
        raise NotImplementedError("Milestone 1 exposes no execution path")
