from __future__ import annotations

import importlib
import importlib.metadata
import inspect
import os
from typing import Any

from p12_recovery.models import BackendDescriptor, CompilationConfig, CostEstimate, ValidationResult


def quantinuum_available() -> bool:
    try:
        importlib.metadata.version("pytket-quantinuum")
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def credentials_detected() -> bool:
    # Presence only; values are never returned or logged.
    names = (
        "QNUX_TOKEN",
        "QUANTINUUM_API_TOKEN",
        "HQS_API_TOKEN",
        "AZURE_QUANTUM_CONNECTION_STRING",
    )
    return any(bool(os.environ.get(name)) for name in names)


def classify_target(device_name: str | None) -> str:
    if not device_name:
        return "unknown"
    lowered = device_name.lower()
    if any(token in lowered for token in ("syntax", "checker")):
        return "syntax_checker"
    if any(token in lowered for token in ("emulator", "simulator", "-e")):
        return "emulator"
    return "physical"


class QuantinuumCompilationBackend:
    def __init__(self, device_name: str | None) -> None:
        self.device_name = device_name
        self._backend: Any | None = None

    def describe(self) -> BackendDescriptor:
        signature = "unavailable"
        if quantinuum_available():
            try:
                module = importlib.import_module("pytket.extensions.quantinuum")
                QuantinuumBackend = module.QuantinuumBackend
                signature = str(inspect.signature(QuantinuumBackend.get_compiled_circuit))
            except (ImportError, TypeError, ValueError):
                pass
        return BackendDescriptor(
            provider="quantinuum",
            device_name=self.device_name,
            target_type=classify_target(self.device_name),  # type: ignore[arg-type]
            sdk_versions={
                "pytket": _version("pytket"),
                "pytket-quantinuum": _version("pytket-quantinuum"),
            },
            credentials_detected=credentials_detected(),
            available=quantinuum_available(),
            notes=[
                "Target classification is name-based until backend metadata is available",
                f"Detected get_compiled_circuit signature: {signature}",
                "Generic compiler seed is recorded but the detected compile method does not accept it",
            ],
        )

    def _instance(self) -> Any:
        if not quantinuum_available():
            raise RuntimeError("pytket-quantinuum is not installed")
        if not self.device_name:
            raise RuntimeError(
                "No Quantinuum target configured; set backend.device_name or P12_QUANTINUUM_DEVICE"
            )
        if self._backend is None:
            from pytket.extensions.quantinuum import QuantinuumBackend  # type: ignore[attr-defined]

            self._backend = QuantinuumBackend(device_name=self.device_name)
        return self._backend

    def compile(self, circuit: Any, config: CompilationConfig) -> Any:
        backend = self._instance()
        level = int(config.compiler.get("optimization_level", 1))
        timeout = int(config.compiler.get("timeout_seconds", 1800))
        return backend.get_compiled_circuit(circuit, optimisation_level=level, timeout=timeout)

    def validate(self, circuit: Any) -> ValidationResult:
        backend = self._instance()
        predicates: dict[str, bool | None] = {}
        diagnostics: list[str] = []
        try:
            for predicate in backend.required_predicates:
                name = type(predicate).__name__
                try:
                    predicates[name] = bool(predicate.verify(circuit))
                except Exception as exc:
                    predicates[name] = None
                    diagnostics.append(f"{name}: {type(exc).__name__}: {exc}")
            predicates["backend.valid_circuit"] = bool(backend.valid_circuit(circuit))
        except Exception as exc:
            diagnostics.append(f"Backend validation failed: {type(exc).__name__}: {exc}")
        return ValidationResult(
            passed=bool(predicates) and all(value is True for value in predicates.values()),
            predicates=predicates,
            diagnostics=diagnostics,
        )

    def estimate_cost(self, circuit: Any, shots: int) -> CostEstimate | None:
        del circuit
        return CostEstimate(
            shots=shots,
            estimated_hqcs=None,
            notes=["No stable offline cost API was detected in pytket-quantinuum 0.59.1"],
        )

    def submit(self, circuit: Any, shots: int) -> Any:
        del circuit, shots
        raise NotImplementedError("Milestone 1 intentionally exposes no Quantinuum submission path")


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None
