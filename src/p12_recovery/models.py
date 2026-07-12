from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import SCHEMA_VERSION


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportBase(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
    git_commit: str | None = None
    python_version: str = Field(default_factory=platform.python_version)
    operating_system: str = Field(default_factory=platform.platform)
    architecture: str = Field(default_factory=platform.machine)
    package_versions: dict[str, str | None] = Field(default_factory=dict)
    input_hashes: dict[str, str] = Field(default_factory=dict)
    configuration_hash: str | None = None
    random_seed: int | None = None


class SourceArtifact(ReportBase):
    circuit_id: str
    source_repository: str
    source_path: str
    retrieval_timestamp_utc: datetime
    source_commit_sha: str | None = None
    local_path: str
    file_size_bytes: int
    sha256: str


class GateStatistics(FrozenModel):
    total_operations: int
    counts_by_gate: dict[str, int]
    one_qubit_gates: int
    two_qubit_gates: int
    greater_than_two_qubit_gates: int
    barriers: int
    resets: int
    measurements: int
    conditional_operations: int
    unsupported_instructions: list[str]
    circuit_depth: int
    one_qubit_depth: int
    two_qubit_depth: int


class InteractionGraphStatistics(FrozenModel):
    number_of_nodes: int
    active_nodes: int
    number_of_edges: int
    density: float
    connected_components: int
    component_sizes: list[int]
    degree_min: float
    degree_mean: float
    degree_median: float
    degree_max: float
    degree_histogram: dict[str, int]
    weighted_degree_min: float
    weighted_degree_mean: float
    weighted_degree_median: float
    weighted_degree_max: float
    diameter: int | None
    component_diameters: list[int]
    average_shortest_path_length: float | None
    frequent_pairs: list[dict[str, Any]]
    fully_connected: bool
    all_qubits_participate: bool


class CircuitInspectionReport(ReportBase):
    circuit_name: str
    source_path: str
    source_sha256: str
    qasm_version: str
    parser: str
    parser_version: str
    number_of_qubits: int
    number_of_classical_bits: int
    quantum_registers: list[dict[str, Any]]
    classical_registers: list[dict[str, Any]]
    used_qubits: list[int]
    unused_qubits: list[int]
    measured_qubits: list[int]
    unmeasured_qubits: list[int]
    source_contains_measurements: bool
    gates: GateStatistics
    has_symbolic_parameters: bool
    symbolic_parameter_count: int
    all_numerical_angles_finite: bool
    minimum_rotation_angle: float | None
    maximum_rotation_angle: float | None
    interaction_graph: InteractionGraphStatistics
    depth_definition: str


class BackendDescriptor(FrozenModel):
    provider: str
    device_name: str | None = None
    target_type: Literal["local", "emulator", "syntax_checker", "physical", "unknown"]
    sdk_versions: dict[str, str | None] = Field(default_factory=dict)
    credentials_detected: bool = False
    available: bool = True
    notes: list[str] = Field(default_factory=list)


class CompilationConfig(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    source_circuit: str
    backend: dict[str, Any]
    compiler: dict[str, Any]
    measurement: dict[str, Any]
    output: dict[str, Any]


class MeasurementEntry(FrozenModel):
    logical_qubit_index: int
    physical_qubit_index: int | None = None
    classical_bit_index: int
    raw_string_position: int
    canonical_string_position: int


class MeasurementMapping(ReportBase):
    number_of_qubits: int
    sdk_string_order: str
    register_layout: list[dict[str, Any]]
    entries: list[MeasurementEntry]

    @model_validator(mode="after")
    def complete_and_unique(self) -> MeasurementMapping:
        fields = {
            "logical": [e.logical_qubit_index for e in self.entries],
            "classical": [e.classical_bit_index for e in self.entries],
            "raw": [e.raw_string_position for e in self.entries],
            "canonical": [e.canonical_string_position for e in self.entries],
        }
        for name, values in fields.items():
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {name} mapping entries")
        if set(fields["logical"]) != set(range(self.number_of_qubits)):
            raise ValueError("Incomplete logical measurement mapping")
        return self


class ValidationResult(FrozenModel):
    passed: bool
    predicates: dict[str, bool | None]
    diagnostics: list[str] = Field(default_factory=list)


class CostEstimate(FrozenModel):
    shots: int
    estimated_hqcs: float | None = None
    notes: list[str] = Field(default_factory=list)


class CompilationReport(ReportBase):
    status: Literal["success", "blocked", "failed"]
    backend: BackendDescriptor
    original: dict[str, Any]
    compiled: dict[str, Any] | None = None
    overhead: dict[str, Any] = Field(default_factory=dict)
    validation: ValidationResult | None = None
    start_timestamp: datetime
    end_timestamp: datetime
    wall_clock_seconds: float
    failure: dict[str, Any] | None = None
    configuration: dict[str, Any]


class RunManifest(ReportBase):
    run_id: str
    command: str
    arguments: list[str]
    start_timestamp: datetime
    end_timestamp: datetime
    exit_status: int
    dirty_working_tree: bool | None = None
    input_paths: dict[str, str] = Field(default_factory=dict)
    output_paths: dict[str, str] = Field(default_factory=dict)
    configuration_path: str | None = None
    backend_mode: str = "offline"
    credentials_detected: bool = False
    hardware_execution_attempted: Literal[False] = False
    paid_resources_consumed: Literal[False] = False


class SyntheticExperimentConfig(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    number_of_qubits: int = 98
    seed: int
    targets: dict[str, Any]
    shot_counts: list[int]
    bootstrap_replicates: int = 1000
    models: dict[str, Any]


class RecoveryCandidate(FrozenModel):
    method_name: str
    canonical_bitstring: str
    number_of_qubits: int
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_shot_count: int
    confidence: dict[str, Any] = Field(default_factory=dict)
    runtime_seconds: float
    warnings: list[str] = Field(default_factory=list)
    configuration_hash: str


class RecoveryReport(ReportBase):
    candidates: list[RecoveryCandidate]
    method_agreement: dict[str, Any]
    scores: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BootstrapReport(ReportBase):
    method_name: str
    replicates: int
    modal_candidate: str
    modal_candidate_frequency: float
    per_bit_selection_probability: list[float]
    hamming_distance_distribution: list[int]
    stable_bits: int
    unstable_bits: int
    unstable_bit_indices: list[int]
    exact_match_stability: float
    per_bit_one_probability_intervals_95: list[tuple[float, float]]
    replicate_candidates: list[str] | None = None


class HardwareReadinessReport(ReportBase):
    ready: bool
    checks: dict[str, bool | None]
    blockers: list[str]
    hardware_execution_enabled: Literal[False] = False


@dataclass(frozen=True)
class TargetScore:
    exact_match: bool
    correct_bits: int
    total_bits: int
    fraction_correct: float
    percentage_correct: float
    hamming_distance: int
    incorrect_indices: tuple[int, ...]


def base_environment() -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "operating_system": platform.platform(),
        "architecture": platform.machine(),
    }
