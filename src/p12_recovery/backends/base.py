from typing import Any, Protocol

from p12_recovery.models import (
    BackendDescriptor,
    CompilationConfig,
    CostEstimate,
    ValidationResult,
)


class CompilationBackend(Protocol):
    def describe(self) -> BackendDescriptor: ...

    def compile(self, circuit: Any, config: CompilationConfig) -> Any: ...

    def validate(self, circuit: Any) -> ValidationResult: ...

    def estimate_cost(self, circuit: Any, shots: int) -> CostEstimate | None: ...

    def submit(self, circuit: Any, shots: int) -> Any: ...
