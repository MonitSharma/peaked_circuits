from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
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
    git_dirty: bool | None = None
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
    provider_api: str = "unknown"
    device_name: str | None = None
    target_type: str = "unknown"
    target_type_source: str = "unknown"
    qubit_capacity: int | None = None
    gate_set: list[str] = Field(default_factory=list)
    classical_register_limit: int | None = None
    backend_version: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    access_status: str = "unknown"
    metadata_source: Literal["live_api", "cached", "offline", "unknown"] = "unknown"
    has_at_least_98_qubits: bool = False
    p12_compatible: bool = False
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
    logical_qubit_name: str
    compiled_qubit_name: str
    compiled_qubit_index: int | None = None
    physical_qubit_index: int | None = None
    classical_register_name: str
    classical_bit_index: int
    raw_provider_position: int
    canonical_position: int
    mapping_source: str
    mapping_confidence: Literal["high", "medium", "low", "unknown"] = "unknown"

    @property
    def raw_string_position(self) -> int:
        return self.raw_provider_position

    @property
    def canonical_string_position(self) -> int:
        return self.canonical_position


class MeasurementMapping(ReportBase):
    number_of_qubits: int
    sdk_string_order: str
    register_layout: list[dict[str, Any]]
    entries: list[MeasurementEntry]
    complete: bool = True
    unknown_permutation_count: int = 0

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
    effective_compilation_config: dict[str, Any] = Field(default_factory=dict)
    mapping_complete: bool = False
    unknown_permutation_count: int = 0


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
    state: str = "NOT_READY"
    evidence: list[ReadinessEvidence] = Field(default_factory=list)


class AvailableDevicesReport(ReportBase):
    status: Literal["success", "partial", "failed"]
    devices: list[BackendDescriptor] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    live_api_access: bool = False
    authenticated_access: bool = False
    discovery_surfaces: dict[str, str] = Field(default_factory=dict)


class ProviderJobMetadata(ReportBase):
    provider: str = "quantinuum"
    device_name: str
    job_id: str
    job_label: str | None = None
    submitted_circuit_hash: str | None = None
    requested_shots: int
    returned_shots: int
    retrieval_timestamp: datetime = Field(default_factory=utc_now)
    job_status: str
    queue_time_seconds: float | None = None
    execution_time_seconds: float | None = None
    reported_cost_hqcs: float | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderRawResult(ReportBase):
    provider: str = "quantinuum"
    device_name: str
    job_id: str
    job_label: str | None = None
    submitted_circuit_hash: str | None = None
    requested_shots: int
    returned_shots: int
    raw_counts: dict[str, int] = Field(default_factory=dict)
    raw_shots: list[Any] = Field(default_factory=list)
    raw_register_layout: list[dict[str, Any]]
    raw_result_order: Literal["msb_left", "lsb_left"]
    retrieval_timestamp: datetime = Field(default_factory=utc_now)
    job_status: str = "retrieved"
    queue_time_seconds: float | None = None
    execution_time_seconds: float | None = None
    reported_cost_hqcs: float | None = None
    calibration_metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalResult(ReportBase):
    job_id: str
    source_provider_result_hash: str
    measurement_mapping_hash: str
    canonical_counts: dict[str, int]
    canonical_shots: list[str] = Field(default_factory=list)
    canonicalized_shots: int
    rejected_records: int = 0
    rejection_reasons: list[str] = Field(default_factory=list)
    conversion_warnings: list[str] = Field(default_factory=list)
    all_outputs_length_98: bool


class MappingValidationCase(FrozenModel):
    case_name: str
    prepared_logical_string: str
    prepared_circuit_hash: str | None = None
    compiled_circuit_hash: str | None = None
    raw_provider_output: str | None = None
    canonical_output: str | None = None
    mapping_correct: bool | None = None
    status: str = "prepared"


class MappingValidationReport(ReportBase):
    status: Literal["passed", "incomplete", "failed"]
    target: str | None = None
    mode: str
    cases: list[MappingValidationCase]
    passed_cases: int = 0
    total_cases: int = 0
    diagnostics: list[str] = Field(default_factory=list)


class QIROutputMappingEntry(FrozenModel):
    logical_qubit_index: int
    logical_qubit_name: str
    pytket_qubit_index: int
    qir_qubit_index: int
    qir_result_index: int
    provider_result_position: int | None = None
    canonical_position: int
    mapping_source: str = "explicit_final_measurement_order"
    mapping_confidence: Literal["verified_locally"] = "verified_locally"


class QIROutputMapping(ReportBase):
    schema_version: str = "1.0"
    number_of_qubits: int
    entries: list[QIROutputMappingEntry]
    logical_to_qir_mapping_verified: bool
    provider_result_order_verified: Literal[False] = False
    qir_profile: str
    qir_sha256: str | None = None

    @model_validator(mode="after")
    def complete_qir_mapping(self) -> QIROutputMapping:
        expected = set(range(self.number_of_qubits))
        for field_name in (
            "logical_qubit_index",
            "pytket_qubit_index",
            "qir_qubit_index",
            "qir_result_index",
            "canonical_position",
        ):
            values = [getattr(entry, field_name) for entry in self.entries]
            if len(values) != len(set(values)) or set(values) != expected:
                raise ValueError(f"Incomplete or duplicate QIR mapping field: {field_name}")
        if any(entry.provider_result_position is not None for entry in self.entries):
            raise ValueError("Milestone 3 must not populate provider_result_position")
        return self


class QIRExportReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["success", "failed"]
    source_qasm_path: str | None = None
    source_qasm_sha256: str
    source_qubits: int
    source_operations: int
    source_two_qubit_gates: int
    source_measurements: int
    transformed_operation_counts: dict[str, int]
    transformed_operations: int
    measurement_count: int
    canonical_order: Literal["logical_q0_to_q97_left_to_right"]
    qir_format: str
    qir_profile: str
    qir_path: str
    qir_sha256: str
    qir_size_bytes: int
    qir_bitcode_path: str
    qir_bitcode_sha256: str
    qir_bitcode_size_bytes: int
    conversion_api: str
    conversion_preflight_passed: bool
    unsupported_operations: list[str] = Field(default_factory=list)
    omitted_operation_count: int = 0
    logical_to_qir_mapping_verified: bool
    provider_result_order_verified: Literal[False] = False


class QIRValidationReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["passed", "failed"]
    input_path: str
    input_sha256: str | None = None
    export_report_path: str | None = None
    evidence_levels: list[
        Literal["structural", "resource_count", "fixture_semantic", "provider_syntax"]
    ] = Field(default_factory=list)
    validation_level: str
    checks: dict[str, bool]
    required_num_qubits: int | None = None
    required_num_results: int | None = None
    measurement_call_count: int | None = None
    result_output_count: int | None = None
    qir_gate_call_count: int | None = None
    logical_to_qir_mapping_verified: bool = False
    provider_result_order_verified: Literal[False] = False
    fixture_semantic_validation_level: str
    diagnostics: list[str] = Field(default_factory=list)


class QIRArtifactManifest(ReportBase):
    schema_version: str = "1.0"
    artifact_paths: dict[str, str]
    artifact_hashes: dict[str, str]
    source_hash: str
    conversion_configuration: dict[str, Any]
    hardware_execution_attempted: Literal[False] = False
    nexus_write_attempted: Literal[False] = False
    hqcs_consumed: Literal[False] = False


class QIRMappingCaseExport(FrozenModel):
    case_name: str
    expected_canonical_string: str
    qir_path: str
    qir_sha256: str
    export_report_path: str
    mapping_path: str
    status: Literal["passed", "failed"]


class QIRMappingCasesReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["passed", "failed"]
    cases: list[QIRMappingCaseExport]
    total_cases: int
    passed_cases: int
    reversal_sensitive: bool
    logical_to_qir_mapping_verified: bool
    provider_result_order_verified: Literal[False] = False


class NexusSyntaxCheckConfig(FrozenModel):
    schema_version: str = "1.0"
    nexus: dict[str, Any]
    artifact: dict[str, Any]
    authorization: dict[str, Any]
    output: dict[str, Any]


class NexusSyntaxCheckJob(ReportBase):
    schema_version: str = "1.0"
    project_ref: str
    qir_artifact_ref: str
    syntax_check_job_ref: str
    target: Literal["Helios-1SC"]
    target_classification: Literal["syntax_checker"]
    submission_timestamp: datetime
    completion_timestamp: datetime | None = None
    final_status: str
    submitted_qir_sha256: str
    text_qir_sha256: str | None = None
    bitcode_sha256: str | None = None
    source_qasm_sha256: str
    reported_cost_hqcs: float | None = None
    hqcs_used: Literal[False] = False
    emulator_or_hardware_execution: Literal[False] = False


class NexusSyntaxCheckReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["passed", "failed", "blocked", "not_submitted"]
    target: str
    target_classification: str
    qir_sha256: str
    text_qir_sha256: str | None = None
    bitcode_sha256: str | None = None
    source_qasm_sha256: str
    project_ref: str | None = None
    qir_artifact_ref: str | None = None
    job_ref: str | None = None
    final_status: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    reported_cost_hqcs: float | None = None
    hqcs_used: Literal[False] = False
    emulator_or_hardware_execution: Literal[False] = False
    provider_result_order_verified: Literal[False] = False


class MappingSyntaxCheckAggregateReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["passed", "failed", "blocked", "not_submitted"]
    target: str
    ordered_cases: list[str]
    case_statuses: dict[str, Any]
    p12_submission_allowed: bool
    local_logical_to_qir_mapping: str
    all_mapping_qir_syntax_checks: str
    p12_qir_syntax_check: str
    provider_result_order: Literal["unresolved"] = "unresolved"


class CostEstimateItem(FrozenModel):
    shots: int
    estimated_hqcs: float | None = None
    estimate_source: str | None = None


class CostEstimateReport(ReportBase):
    status: Literal["supported", "unsupported", "failed"]
    target: str
    estimates: list[CostEstimateItem]
    reason: str | None = None
    sdk_version: str | None = None
    provenance: str | None = None
    manual_action_required: bool = False


class NexusCostItem(FrozenModel):
    program_name: str
    bitcode_sha256: str
    target: Literal["Helios-1E"]
    shots: int
    estimated_hqcs: float
    confidence: float
    cost_job_ref: str | None = None
    provider_timestamp: datetime = Field(default_factory=utc_now)
    api_used: str = "qnexus.qir.cost_confidence"
    remote_costing_job_created: Literal[True] = True


class NexusCostReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["supported", "failed"]
    target: str
    items: list[NexusCostItem] = Field(default_factory=list)
    api_used: str
    remote_costing_job_created: bool
    cost_job_reference_available_from_api: bool = False
    diagnostics: list[str] = Field(default_factory=list)


class RawProviderResultReport(ReportBase):
    schema_version: str = "1.0"
    target: str
    case_name: str
    job_ref: str
    result_ref: str
    result_type: str
    raw_payload: Any
    raw_payload_sha256: str
    requested_shots: int
    returned_shots: int
    reported_cost_hqcs: float | None = None


class ProviderOutputMappingReport(ReportBase):
    schema_version: str = "1.0"
    provider_result_order_verified: bool
    emulator_mapping_validation_passed: bool
    resolved_positions: int
    unresolved_positions: int
    provider_layout: list[str]
    entries: list[dict[str, Any]]
    case_reports: dict[str, Any]


class EmulatorMappingAggregateReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["passed", "failed", "incomplete"]
    target: str
    ordered_cases: list[str]
    case_statuses: dict[str, Any]
    provider_result_order_verified: bool = False
    emulator_mapping_validation_passed: bool = False
    resolved_positions: int = 0
    unresolved_positions: int = 98
    max_cost_per_job: float
    shots_per_case: int


class EmulatorAuthorizationEvidence(ReportBase):
    schema_version: str = "1.0"
    target: str
    target_classification: str
    execute_emulator_flag: bool
    environment_authorized: bool
    authenticated_discovery: bool
    cost_evidence_exists: bool
    max_cost: float
    interactive_confirmed: bool
    physical_hardware_forbidden: Literal[True] = True


class P12EmulatorPilotReport(ReportBase):
    schema_version: str = "1.0"
    status: Literal["passed", "failed", "blocked", "not_run"]
    target: str
    shots: int
    max_cost: float
    job_ref: str | None = None
    final_status: str | None = None
    failure_stage: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    simulator_configuration: dict[str, Any] = Field(default_factory=dict)
    reported_cost_hqcs: float | None = None
    normalized_width: int | None = None
    hidden_target_scored: Literal[False] = False


class ProtocolFreezeRecord(ReportBase):
    status: Literal["frozen"]
    protocol_hash: str
    configuration_path: str
    configuration: dict[str, Any]
    prerequisites: dict[str, bool]


class ReadinessState(StrEnum):
    NOT_READY = "NOT_READY"
    READY_FOR_OFFLINE_ANALYSIS = "READY_FOR_OFFLINE_ANALYSIS"
    READY_FOR_COMPILE_ONLY = "READY_FOR_COMPILE_ONLY"
    READY_FOR_QIR_EXPORT = "READY_FOR_QIR_EXPORT"
    READY_FOR_SYNTAX_CHECK = "READY_FOR_SYNTAX_CHECK"
    READY_FOR_EMULATOR_MAPPING_VALIDATION = "READY_FOR_EMULATOR_MAPPING_VALIDATION"
    EMULATOR_MAPPING_VALIDATED = "EMULATOR_MAPPING_VALIDATED"
    READY_FOR_P12_EMULATOR_PILOT = "READY_FOR_P12_EMULATOR_PILOT"
    P12_EMULATOR_PILOT_COMPLETE = "P12_EMULATOR_PILOT_COMPLETE"


class ReadinessEvidence(FrozenModel):
    check: str
    passed: bool
    evidence_path: str | None = None
    evidence_hash: str | None = None
    details: str


class ReadinessEvidenceReport(ReportBase):
    state: ReadinessState
    evidence: list[ReadinessEvidence]
    blockers: list[str]


class PublicAuditFinding(FrozenModel):
    check: str
    passed: bool
    details: str
    paths: list[str] = Field(default_factory=list)


class PublicAuditReport(ReportBase):
    passed: bool
    findings: list[PublicAuditFinding]
    scanned_files: int


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
