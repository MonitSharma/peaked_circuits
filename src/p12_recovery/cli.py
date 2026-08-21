from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

import typer
import yaml
from pydantic import BaseModel
from rich.console import Console

from .acquisition import fetch_source
from .backends.quantinuum import (
    credentials_detected,
    discover_quantinuum_report,
    qnexus_available,
    quantinuum_available,
    sanitize_diagnostic,
)
from .batch_analysis import analyze_batch, analyze_batches
from .benchmark import run_synthetic_benchmark
from .campaign import BatchRole, BatchStatus, CampaignStatus, CampaignStore, operational_max_cost
from .candidate_freeze import freeze_candidate
from .circuit_inspection import inspect_circuit
from .compilation import compile_from_config, validate_existing
from .config import load_model
from .constants import DEFAULT_QASM
from .cost_estimation import estimate_costs
from .counts_io import load_aggregated_counts
from .emulator_guard import (
    HeliosEmulatorExecutionBlocked,
    assert_helios_emulator_execution_allowed,
)
from .hashing import hash_config, read_sha256sums, sha256_file
from .mapping_validation import run_mapping_validation
from .models import (
    AvailableDevicesReport,
    CanonicalResult,
    CircuitInspectionReport,
    CompilationReport,
    CostEstimateReport,
    EmulatorAuthorizationEvidence,
    EmulatorMappingAggregateReport,
    MappingSyntaxCheckAggregateReport,
    MappingValidationReport,
    MeasurementMapping,
    NexusCostReport,
    NexusSyntaxCheckConfig,
    NexusSyntaxCheckJob,
    NexusSyntaxCheckReport,
    P12EmulatorPilotReport,
    ProtocolFreezeRecord,
    ProviderOutputMappingReport,
    ProviderRawResult,
    PublicAuditReport,
    QIRExportReport,
    QIRMappingCasesReport,
    QIROutputMapping,
    QIRValidationReport,
    RawProviderResultReport,
    ReadinessEvidenceReport,
    RecoveryReport,
    RunManifest,
    SyntheticExperimentConfig,
)
from .nexus_cost import (
    estimate_nexus_qir_costs,
    mapping_cost_programs,
    p12_cost_program,
    write_nexus_cost_report,
)
from .nexus_emulator import execute_mapping_cases, execute_p12_pilot
from .nexus_hardware import (
    HardwarePreflight,
    build_preflight_report,
    dry_run_hardware_batch,
    poll_hardware_batch,
    reconcile_hardware_batch,
    retrieve_hardware_batch,
    submit_hardware_batch,
)
from .nexus_syntax_check import (
    MAPPING_CASE_ORDER,
    submit_mapping_syntax_checks,
    submit_validated_syntax_check,
    update_mapping_aggregate_with_p12,
    write_blocked_syntax_report,
    write_failed_syntax_report,
)
from .protocol import ProtocolFreezeBlocked, freeze_protocol
from .provider_results import (
    load_provider_result,
    persist_imported_result,
    retrieve_existing_quantinuum_job,
)
from .public_audit import run_public_audit
from .qir_export import QIRExportError, export_mapping_qir_cases, export_p12_qir
from .qir_validation import validate_qir_artifact
from .readiness import build_readiness
from .recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)
from .reporting import (
    git_dirty_paths,
    git_state,
    inspection_markdown,
    package_versions,
    save_inspection_figures,
    write_json,
    write_manifest,
)
from .syntax_check_guard import NexusSyntaxCheckBlocked, assert_nexus_syntax_check_allowed

app = typer.Typer(no_args_is_help=True, help="Hardware-safe P12 feasibility and recovery pipeline.")
console = Console()


def _root() -> Path:
    current = Path.cwd().resolve()
    if (current / "pyproject.toml").is_file():
        return current
    raise typer.BadParameter("Run the CLI from the p12-helios-recovery repository root")


def _ensure_campaign(root: Path, batch_id: str, shots: int, max_cost: float | None) -> tuple[CampaignStore, Any, Any]:
    store = CampaignStore(root)
    cost_payload = json.loads((root / "results/nexus/cost/p12_cost.json").read_text())
    item = next((value for value in cost_payload.get("items", []) if value.get("shots") == shots), None)
    predicted = float(item["estimated_hqcs"]) if item else None
    state = store.initialize(
        source=root / "circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm",
        qir=root / "results/qir/p12.ll",
        bitcode=root / "results/qir/p12.bc",
        protocol_version="3.0",
        recommended_shots=400,
        predicted_hqc=predicted,
    )
    config = yaml.safe_load((root / "configs/experiment.yaml").read_text())
    state.protocol_hash = hash_config(config)
    if batch_id not in state.batches:
        role = BatchRole.DISCOVERY if batch_id == "batch_001" else BatchRole.CONFIRMATION if batch_id == "batch_002" else BatchRole.ADDITIONAL_REPLICATION
        batch = store.create_batch(state, role=role, shots=shots, max_cost=max_cost or (operational_max_cost(predicted) if predicted else None))
    else:
        batch = state.batches[batch_id]
        if batch.requested_shots != shots:
            raise typer.BadParameter(f"Existing {batch_id} uses {batch.requested_shots} shots")
    current_commit, current_dirty = git_state(root)
    if batch.repository_git_sha != current_commit:
        batch.repository_git_sha = current_commit
    if current_dirty:
        raise typer.BadParameter("Campaign provenance requires a clean Git tree")
    store.save(state)
    return store, state, batch


def _refresh_p12_cost(root: Path, shots: int) -> NexusCostReport:
    """Refresh exactly one P12 cost row immediately before a hardware preflight."""
    qir_path = root / "results/qir/p12.ll"
    fresh = estimate_nexus_qir_costs(
        root,
        target="Helios-1E",
        programs=p12_cost_program(root, qir_path),
        shots=[shots],
    )
    if fresh.status != "supported":
        return fresh
    path = root / "results/nexus/cost/p12_cost.json"
    existing = NexusCostReport.model_validate_json(path.read_text()) if path.is_file() else fresh
    refreshed = [
        item for item in existing.items if not (item.program_name == "p12" and item.shots == shots)
    ] + fresh.items
    merged = existing.model_copy(update={"status": "supported", "items": refreshed})
    write_nexus_cost_report(root, merged, mapping_cases=False)
    return merged


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


@app.command()
def doctor() -> None:
    """Report local readiness without authenticating or contacting a provider."""
    root = _root()
    qasm = root / DEFAULT_QASM
    sums = qasm.parent / "SHA256SUMS"
    checksum_ok = False
    if qasm.is_file() and sums.is_file():
        checksum_ok = read_sha256sums(sums).get(qasm.name) == sha256_file(qasm)
    values = {
        "Python": platform.python_version(),
        "Platform": platform.platform(),
        "Architecture": platform.machine(),
        "pytket": _version("pytket"),
        "pytket-quantinuum": _version("pytket-quantinuum"),
        "pytket-qir": _version("pytket-qir"),
        "pyqir": _version("pyqir"),
        "qnexus": _version("qnexus"),
        "qiskit": _version("qiskit"),
        "Credentials detected": credentials_detected(),
        "Configured backend": os.environ.get("P12_QUANTINUUM_DEVICE") or "not configured",
        "Hardware enabled": os.environ.get("P12_ENABLE_HARDWARE") == "1",
        "QASM exists": qasm.is_file(),
        "QASM checksum matches": checksum_ok,
        "Ready for inspection": qasm.is_file() and checksum_ok,
        "Ready for legacy local compilation": qasm.is_file() and quantinuum_available(),
        "Nexus client installed": qnexus_available(),
        "Ready for QIR export": qasm.is_file() and _version("pytket-qir") is not None,
        "Ready for emulator validation": bool(os.environ.get("P12_QUANTINUUM_DEVICE"))
        and quantinuum_available(),
        "Ready for hardware submission": False,
    }
    for key, value in values.items():
        console.print(f"{key}: {value}")
    if qasm.is_file() and quantinuum_available():
        console.print("READY_FOR_COMPILE_ONLY")
    elif qasm.is_file():
        console.print("READY_FOR_OFFLINE_ANALYSIS")
    else:
        console.print("NOT_READY")


@app.command()
def fetch(replace_source: Annotated[bool, typer.Option("--replace-source")] = False) -> None:
    """Resolve the exact registry ID, download the QASM, and freeze its hash."""
    root, start = _root(), datetime.now(UTC)
    artifact = fetch_source(root, replace_source=replace_source)
    metadata = root / "circuits/original/source_metadata.json"
    write_manifest(
        root,
        command="fetch",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        outputs=[
            Path(artifact.local_path),
            metadata,
            Path(artifact.local_path).parent / "SHA256SUMS",
        ],
    )
    console.print(f"Verified {artifact.circuit_id}: {artifact.sha256}")


@app.command(name="inspect")
def inspect_command(
    source: Annotated[Path | None, typer.Option("--source")] = None,
    no_figures: Annotated[bool, typer.Option("--no-figures")] = False,
) -> None:
    """Inspect QASM structure and interaction statistics; never simulate 98 qubits."""
    root, start = _root(), datetime.now(UTC)
    path = source or root / DEFAULT_QASM
    if not path.is_absolute():
        path = root / path
    report, _ = inspect_circuit(path)
    json_path = root / "results/inspection/inspection_report.json"
    md_path = root / "results/inspection/inspection_report.md"
    write_json(json_path, report)
    md_path.write_text(inspection_markdown(report))
    if not no_figures:
        save_inspection_figures(report, root / "results/figures")
    write_manifest(
        root,
        command="inspect",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        inputs=[path],
        outputs=[json_path, md_path],
    )
    console.print(
        f"Inspected {report.number_of_qubits} qubits and {report.gates.total_operations} operations"
    )


@app.command(name="compile")
def compile_command(
    config: Annotated[Path, typer.Option("--config")] = Path("configs/compilation.yaml"),
    target: Annotated[str | None, typer.Option("--target")] = None,
) -> None:
    """Compile only; this command has no submission capability."""
    root, start = _root(), datetime.now(UTC)
    path = config if config.is_absolute() else root / config
    report = compile_from_config(root, path, device_name_override=target)
    output = root / "results/compilation/compilation_report.json"
    write_manifest(
        root,
        command="compile",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        inputs=[root / DEFAULT_QASM, path],
        outputs=[output],
        config=path,
        seed=report.random_seed,
        backend_mode="compile_only",
        credentials_detected=report.backend.credentials_detected,
    )
    console.print(f"Compilation status: {report.status}")
    if report.failure:
        console.print(report.failure["sanitized_message"])


@app.command()
def devices(
    json_output: Annotated[bool, typer.Option("--json")] = False,
    only_p12_compatible: Annotated[bool, typer.Option("--only-p12-compatible")] = False,
    refresh: Annotated[bool, typer.Option("--refresh")] = False,
) -> None:
    """Discover live Quantinuum targets; never submit a circuit."""
    del refresh  # Every invocation is a live refresh; retained for an explicit stable CLI.
    root, start = _root(), datetime.now(UTC)
    report = discover_quantinuum_report()
    output = root / "results/backend/available_devices.json"
    markdown = root / "results/backend/available_devices.md"
    write_json(output, report)
    rows = report.devices
    visible = [item for item in rows if item.p12_compatible] if only_p12_compatible else rows
    table = "\n".join(
        f"| {item.device_name} | {item.provider_api} | {item.target_type} | {item.qubit_capacity or 'unknown'} | "
        f"{'yes' if item.p12_compatible else 'no'} | {', '.join(item.gate_set)} | {item.access_status} |"
        for item in rows
    )
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(
        "# Available Quantinuum devices\n\n"
        f"Status: **{report.status}**\n\n"
        f"Authenticated Nexus access: **{report.authenticated_access}**\n\n"
        "| Device | API surface | Type | Qubits | P12 compatible | Gate set | Access status |\n"
        "|---|---|---:|---:|---:|---|---|\n"
        + (table or "| none | unknown | unknown | unknown | no | | unavailable |")
        + "\n"
    )
    write_manifest(
        root,
        command="devices",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0 if report.status != "failed" else 1,
        outputs=[output, markdown],
        backend_mode="discovery_only",
        credentials_detected=credentials_detected(),
    )
    if json_output:
        console.print_json(data=[item.model_dump(mode="json") for item in visible])
    else:
        if not visible:
            console.print(
                "No P12-compatible targets were discovered."
                if only_p12_compatible
                else "No targets were discovered."
            )
        for item in visible:
            console.print(
                f"{item.device_name}: api={item.provider_api}, {item.target_type}, "
                f"qubits={item.qubit_capacity}, "
                f"p12_compatible={item.p12_compatible}, access={item.access_status}"
            )
        for diagnostic in report.diagnostics:
            console.print(f"Discovery unavailable: {diagnostic}")


@app.command()
def validate() -> None:
    """Validate the existing compile-only result."""
    root, start = _root(), datetime.now(UTC)
    result = validate_existing(root)
    output = root / "results/compilation/validation_result.json"
    write_manifest(
        root,
        command="validate",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        inputs=[root / "results/compilation/compilation_report.json"],
        outputs=[output],
        backend_mode="compile_only",
    )
    console.print(f"Validation passed: {result.passed}")
    for diagnostic in result.diagnostics:
        console.print(diagnostic)


@app.command()
def synthetic(
    config: Annotated[Path, typer.Option("--config")] = Path("configs/synthetic.yaml"),
    smoke: Annotated[bool, typer.Option("--smoke")] = False,
) -> None:
    """Benchmark recovery on a planted synthetic target."""
    root, start = _root(), datetime.now(UTC)
    path = config if config.is_absolute() else root / config
    model = load_model(path, SyntheticExperimentConfig)
    run_synthetic_benchmark(
        model, root / "results/synthetic", root / "results/figures", smoke=smoke
    )
    outputs = [
        root / "results/synthetic/synthetic_report.json",
        root / "results/synthetic/synthetic_summary.csv",
        root / "results/synthetic/synthetic_report.md",
    ]
    write_manifest(
        root,
        command="synthetic",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        inputs=[path],
        outputs=outputs,
        config=path,
        seed=model.seed,
    )
    console.print(f"Synthetic benchmark complete (seed={model.seed}, smoke={smoke})")


@app.command(name="analyze-counts")
def analyze_counts(path: Path) -> None:
    """Analyze strictly canonical aggregated counts."""
    root, start = _root(), datetime.now(UTC)
    payload = load_aggregated_counts(path)
    if payload["bit_order"] != "canonical":
        raise typer.BadParameter(
            "Provider-raw counts require an explicit MeasurementMapping; refusing to guess"
        )
    counts = payload["counts"]
    candidates = [
        most_frequent_string(counts),
        bitwise_majority_string(counts),
        weighted_observed_medoid(counts),
        cluster_consensus(counts),
    ]
    report = RecoveryReport(
        candidates=candidates,
        method_agreement=method_agreement(candidates),
        input_hashes={str(path): sha256_file(path)},
        package_versions=package_versions(),
    )
    output = root / "results/recovery_report.json"
    write_json(output, report)
    write_manifest(
        root,
        command="analyze-counts",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        inputs=[path],
        outputs=[output],
    )
    console.print(f"Analyzed {payload['shots']} canonical shots")


@app.command(name="build-report")
def build_report() -> None:
    """Build evidence-based Milestone 3 readiness."""
    root, start = _root(), datetime.now(UTC)
    report = build_readiness(root)
    output = root / "results/hardware_readiness_report.json"
    write_manifest(
        root,
        command="build-report",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        outputs=[output, root / "docs/hardware_readiness.md"],
    )
    console.print(report.state)


@app.command(name="hardware-preflight")
def hardware_preflight_command(
    batch: Annotated[str, typer.Option("--batch")] = "batch_001",
    shots: Annotated[int, typer.Option("--shots", min=1)] = 400,
    max_cost: Annotated[float | None, typer.Option("--max-cost")] = None,
) -> None:
    """Validate a future physical batch without submitting it."""
    root, start = _root(), datetime.now(UTC)
    fresh_cost = _refresh_p12_cost(root, shots)
    if fresh_cost.status != "supported":
        raise typer.BadParameter("Fresh provider cost estimation failed")
    _store, state, record = _ensure_campaign(root, batch, shots, max_cost)
    discovery = discover_quantinuum_report().model_dump(mode="json")
    item = next((value for value in fresh_cost.items if value.program_name == "p12" and value.shots == shots), None)
    predicted = item.estimated_hqcs if item else None
    report = build_preflight_report(root, state, batch, discovery=discovery, predicted_hqc=predicted, max_cost=record.max_cost)
    directory = root / "hardware_campaign" / batch / "preflight"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "preflight.json").write_text(report.model_dump_json(indent=2) + "\n")
    (directory / "preflight.md").write_text(
        f"# {batch} hardware preflight\n\nStatus: **{'passed' if report.passed else 'blocked'}**\n\n"
        + "\n".join(f"- [{'x' if value else ' '}] {key}" for key, value in report.checks.items())
        + "\n\n`hardware_submission_authorized_by_user = false`\n"
    )
    write_manifest(root, command="hardware-preflight", arguments=sys.argv[1:], start=start, exit_status=0, outputs=[directory / "preflight.json", directory / "preflight.md"], backend_mode="hardware_preflight_only")
    console.print(f"Hardware preflight {batch}: {'passed' if report.passed else 'blocked'}")


@app.command(name="hardware-submit")
def hardware_submit_command(
    batch: Annotated[str, typer.Option("--batch")] = "batch_001",
    shots: Annotated[int, typer.Option("--shots", min=1)] = 400,
    max_cost: Annotated[float | None, typer.Option("--max-cost")] = None,
    execute_hardware: Annotated[bool, typer.Option("--execute-hardware")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Render or, only with all explicit gates, submit one physical batch."""
    root, start = _root(), datetime.now(UTC)
    fresh_cost = _refresh_p12_cost(root, shots)
    if fresh_cost.status != "supported":
        raise typer.BadParameter("Fresh provider cost estimation failed")
    _store, state, record = _ensure_campaign(root, batch, shots, max_cost)
    discovery = discover_quantinuum_report().model_dump(mode="json")
    item = next((value for value in fresh_cost.items if value.program_name == "p12" and value.shots == shots), None)
    predicted = item.estimated_hqcs if item else None
    report = build_preflight_report(root, state, batch, discovery=discovery, predicted_hqc=predicted, max_cost=record.max_cost)
    if dry_run or not execute_hardware:
        deterministic_name = f"p12-physical-{batch}-{state.qir_bitcode_sha256[:8]}-{(state.protocol_hash or '')[:8]}"
        rendered = dry_run_hardware_batch(root, report, job_name=deterministic_name)
        console.print_json(json.dumps(rendered, sort_keys=True))
        write_manifest(root, command="hardware-submit-dry-run", arguments=sys.argv[1:], start=start, exit_status=0, outputs=[], backend_mode="hardware_dry_run")
        return
    if not report.structural_passed:
        raise typer.BadParameter("; ".join(report.blockers))
    confirmed = typer.confirm(f"Type approval for {batch}: Helios-1, {shots} shots, predicted {predicted} HQC, max_cost {record.max_cost} HQC. Continue?")
    result = submit_hardware_batch(root, state, batch, preflight=HardwarePreflight(target="Helios-1", target_type="hardware", qubit_capacity=98, source_qasm_sha256=state.source_qasm_sha256, qir_sha256=state.qir_sha256, bitcode_sha256=state.qir_bitcode_sha256, syntax_check_passed=True, mapping_verified=True, predicted_hqc=predicted or 0, requested_shots=shots, max_cost=record.max_cost or 0, protocol_frozen=True, campaign_valid=True, no_active_job=True), execute_hardware=True, interactive_confirmed=confirmed)
    console.print_json(json.dumps(result, sort_keys=True))


@app.command(name="hardware-status")
def hardware_status_command(batch: Annotated[str | None, typer.Option("--batch")] = None) -> None:
    """Query saved provider jobs and persist status; never resubmit."""
    root = _root()
    state = CampaignStore(root).load()
    selected = [batch] if batch else list(state.batches)
    for batch_id in selected:
        record = state.batches.get(batch_id)
        if record is None:
            raise typer.BadParameter(f"Unknown batch: {batch_id}")
        if not record.execution_job_ref:
            console.print(f"{batch_id}: role={record.role} status={record.status} job=none")
            continue
        result = poll_hardware_batch(root, state, batch_id)
        console.print(f"{batch_id}: role={record.role} status={result['status']} job={result['job_ref']}")


@app.command(name="hardware-retrieve")
def hardware_retrieve_command(batch: Annotated[str, typer.Option("--batch")]) -> None:
    """Retrieve an existing saved job without creating a new one."""
    root = _root()
    state = CampaignStore(root).load()
    directory = retrieve_hardware_batch(root, state, batch)
    console.print(f"Retrieved {batch} into {directory}")


@app.command(name="hardware-reconcile")
def hardware_reconcile_command(batch: Annotated[str, typer.Option("--batch")]) -> None:
    """Reconcile a persisted pending submission by deterministic provider name."""
    root = _root()
    state = CampaignStore(root).load()
    job_id = reconcile_hardware_batch(root, state, batch)
    console.print(f"Reconciled {batch} to existing provider job {job_id}")


@app.command(name="analyze-hardware-batch")
def analyze_hardware_batch_command(
    batch: Annotated[str, typer.Option("--batch")],
    counts: Annotated[Path, typer.Option("--counts")],
) -> None:
    """Analyze one canonical batch without accessing any target."""
    root, start = _root(), datetime.now(UTC)
    state = CampaignStore(root).load()
    if batch not in state.batches:
        raise typer.BadParameter(f"Unknown batch: {batch}")
    counts_path = counts if counts.is_absolute() else root / counts
    payload = load_aggregated_counts(counts_path)
    report = analyze_batch(payload["counts"])
    output = root / "hardware_campaign" / batch / "analysis" / "analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    CampaignStore(root).update_batch(state, batch, status=BatchStatus.ANALYZED, valid_shots=payload["shots"], analysis_hash=sha256_file(output))
    write_manifest(root, command="analyze-hardware-batch", arguments=sys.argv[1:], start=start, exit_status=0, inputs=[counts_path], outputs=[output], backend_mode="offline_target_blind_analysis")
    console.print(f"Analyzed {batch}: {report['primary_candidate']}")


@app.command(name="analyze-cumulative")
def analyze_cumulative_command(
    counts: Annotated[list[Path], typer.Option("--counts")],
) -> None:
    """Analyze independent canonical batches with pooled and leave-one-batch-out diagnostics."""
    root, start = _root(), datetime.now(UTC)
    paths = [path if path.is_absolute() else root / path for path in counts]
    if not paths:
        raise typer.BadParameter("Provide at least one --counts path")
    payloads = [load_aggregated_counts(path) for path in paths]
    report = analyze_batches([payload["counts"] for payload in payloads])
    output = root / "hardware_campaign" / "cumulative" / "analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_manifest(root, command="analyze-cumulative", arguments=sys.argv[1:], start=start, exit_status=0, inputs=paths, outputs=[output], backend_mode="offline_target_blind_analysis")
    console.print(f"Analyzed {len(paths)} independent batches")


@app.command(name="freeze-candidate")
def freeze_candidate_command(
    batch: Annotated[str, typer.Option("--batch")],
    candidate: Annotated[str | None, typer.Option("--candidate")] = None,
    counts: Annotated[Path | None, typer.Option("--counts")] = None,
) -> None:
    """Freeze the discovery candidate and unlock confirmation batches."""
    root = _root()
    store = CampaignStore(root)
    state = store.load()
    if state.batches.get(batch) is None or state.batches[batch].role != BatchRole.DISCOVERY:
        raise typer.BadParameter("Candidate freezing requires an existing discovery batch")
    analysis_path = root / "hardware_campaign" / batch / "analysis" / "analysis.json"
    if candidate is None:
        if not analysis_path.is_file():
            raise typer.BadParameter("Run analyze-hardware-batch or provide --candidate")
        candidate = json.loads(analysis_path.read_text())["primary_candidate"]
    counts_path = counts if counts and counts.is_absolute() else root / counts if counts else None
    if counts_path is None:
        raise typer.BadParameter("Provide --counts so the freeze is hash-addressed")
    payload = load_aggregated_counts(counts_path)
    protocol_hash = state.protocol_hash or ""
    frozen = freeze_candidate(candidate, counts=payload["counts"], source_paths=[counts_path], protocol_hash=protocol_hash)
    freeze_path = root / "hardware_campaign" / batch / "candidate_freeze.json"
    if freeze_path.is_file() and json.loads(freeze_path.read_text()).get("freeze_hash") != frozen["freeze_hash"]:
        raise typer.BadParameter("Candidate freeze already exists with different content")
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_path.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    state.candidate_freeze = frozen
    state.status = CampaignStatus.DISCOVERY_CANDIDATE_FROZEN
    store.save(state)
    console.print(f"Candidate frozen: {frozen['candidate_sha256']}")


@app.command(name="campaign-status")
def campaign_status_command() -> None:
    """Show persistent campaign and batch state."""
    root = _root()
    state = CampaignStore(root).load()
    console.print(f"Campaign: {state.campaign_id}\nCircuit: {state.circuit_id}\nStatus: {state.status}\nCumulative valid shots: {state.cumulative_valid_shots}")
    for record in state.batches.values():
        console.print(f"  {record.batch_id}: role={record.role} status={record.status} shots={record.requested_shots} job={record.execution_job_ref or 'none'}")


@app.command(name="import-quantinuum-result")
def import_quantinuum_result(
    mapping: Annotated[Path, typer.Option("--mapping")],
    input_path: Annotated[Path | None, typer.Option("--input")] = None,
    job_id: Annotated[str | None, typer.Option("--job-id")] = None,
    target: Annotated[str | None, typer.Option("--target")] = None,
) -> None:
    """Retrieve an existing job or import a saved result; never submit work."""
    if bool(input_path) == bool(job_id):
        raise typer.BadParameter("Provide exactly one of --input or --job-id")
    root, start = _root(), datetime.now(UTC)
    mapping_path = mapping if mapping.is_absolute() else root / mapping
    mapping_model = MeasurementMapping.model_validate_json(mapping_path.read_text())
    if input_path:
        provider_path = input_path if input_path.is_absolute() else root / input_path
        raw = load_provider_result(provider_path)
        inputs = [provider_path, mapping_path]
    else:
        device = target or os.environ.get("P12_QUANTINUUM_DEVICE")
        if not device:
            compilation_path = root / "results/compilation/compilation_report.json"
            if compilation_path.is_file():
                device = CompilationReport.model_validate_json(
                    compilation_path.read_text()
                ).backend.device_name
        if not device:
            raise typer.BadParameter("Existing-job retrieval requires an exact target name")
        raw = retrieve_existing_quantinuum_job(cast(str, job_id), device)
        inputs = [mapping_path]
    outputs = persist_imported_result(root, raw, mapping_model)
    write_manifest(
        root,
        command="import-quantinuum-result",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        inputs=inputs,
        outputs=list(outputs.values()),
        backend_mode="result_retrieval_only",
        credentials_detected=credentials_detected(),
    )
    console.print(f"Normalized {raw.returned_shots} shots for existing job {raw.job_id}")


@app.command(name="mapping-check")
def mapping_check(
    target: Annotated[str | None, typer.Option("--target")] = None,
    mode: Annotated[str, typer.Option("--mode")] = "emulator",
) -> None:
    """Prepare and optionally compile deterministic mapping circuits; never submit."""
    root, start = _root(), datetime.now(UTC)
    report = run_mapping_validation(root, target=target, mode=mode)
    output = root / "results/mapping_validation/mapping_validation_report.json"
    write_manifest(
        root,
        command="mapping-check",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        outputs=[output],
        backend_mode="emulator_compile_only",
    )
    console.print(f"Mapping validation status: {report.status}")


@app.command(name="export-qir")
def export_qir_command(
    source: Annotated[Path, typer.Option("--source")] = Path(DEFAULT_QASM),
    output: Annotated[Path, typer.Option("--output")] = Path("results/qir/p12.ll"),
) -> None:
    """Export frozen P12 to deterministic textual QIR and LLVM bitcode locally."""
    root, start = _root(), datetime.now(UTC)
    source_path = source if source.is_absolute() else root / source
    output_path = output if output.is_absolute() else root / output
    try:
        report = export_p12_qir(root, source_path, output_path)
    except QIRExportError as exc:
        console.print(f"QIR export failed: {exc}")
        raise typer.Exit(1) from exc
    outputs = [
        output_path,
        output_path.with_suffix(".bc"),
        output_path.parent / "qir_export_report.json",
        output_path.parent / "qir_export_report.md",
        output_path.parent / "qir_output_mapping.json",
        output_path.parent / "qir_manifest.json",
    ]
    write_manifest(
        root,
        command="export-qir",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        inputs=[source_path],
        outputs=outputs,
        backend_mode="local_qir_export",
    )
    console.print(
        f"Exported {report.measurement_count} measurements; QIR SHA-256={report.qir_sha256}"
    )


@app.command(name="validate-qir")
def validate_qir_command(
    input_path: Annotated[Path, typer.Option("--input")] = Path("results/qir/p12.ll"),
) -> None:
    """Strictly validate local QIR without contacting Nexus."""
    root, start = _root(), datetime.now(UTC)
    path = input_path if input_path.is_absolute() else root / input_path
    report = validate_qir_artifact(root, path)
    output = root / "results/qir/qir_validation_report.json"
    write_manifest(
        root,
        command="validate-qir",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0 if report.status == "passed" else 1,
        inputs=[path],
        outputs=[output, root / "results/qir/qir_validation_report.md"],
        backend_mode="local_qir_validation",
    )
    console.print(f"QIR validation: {report.status} ({report.validation_level})")
    if report.status != "passed":
        raise typer.Exit(1)


@app.command(name="export-mapping-qir")
def export_mapping_qir_command() -> None:
    """Export all six deterministic 98-qubit mapping cases through the P12 QIR path."""
    root, start = _root(), datetime.now(UTC)
    report = export_mapping_qir_cases(root)
    output = root / "results/qir/mapping_cases/mapping_qir_export_report.json"
    write_manifest(
        root,
        command="export-mapping-qir",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0 if report.status == "passed" else 1,
        outputs=[output],
        backend_mode="local_qir_mapping_export",
    )
    console.print(f"Mapping QIR export: {report.passed_cases}/{report.total_cases} passed")


@app.command(name="nexus-syntax-check")
def nexus_syntax_check_command(
    target: Annotated[str, typer.Option("--target")] = "Helios-1SC",
    qir: Annotated[Path, typer.Option("--qir")] = Path("results/qir/p12.ll"),
    mapping_cases: Annotated[bool, typer.Option("--mapping-cases")] = False,
    mapping_case: Annotated[str | None, typer.Option("--mapping-case")] = None,
    submit_syntax_check: Annotated[bool, typer.Option("--submit-syntax-check")] = False,
    config: Annotated[Path, typer.Option("--config")] = Path("configs/nexus_syntax_check.yaml"),
) -> None:
    """Guarded free Helios-1SC syntax check; never target emulator or hardware."""
    if mapping_case is not None:
        mapping_cases = True
    root, start = _root(), datetime.now(UTC)
    config_path = config if config.is_absolute() else root / config
    settings = load_model(config_path, NexusSyntaxCheckConfig)
    qir_path = qir if qir.is_absolute() else root / qir
    export_path = qir_path.parent / "qir_export_report.json"
    export = QIRExportReport.model_validate_json(export_path.read_text())
    validation = validate_qir_artifact(root, qir_path, export_report_path=export_path)
    discovery = discover_quantinuum_report()
    nexus_devices = [device for device in discovery.devices if device.provider_api == "nexus"]
    descriptor = next((device for device in nexus_devices if device.device_name == target), None)
    target_type = descriptor.target_type if descriptor else "unknown"
    discovered = {device.device_name for device in nexus_devices if device.device_name}
    mapping_report_path = root / "results/nexus/syntax_check/mapping_cases_report.json"
    mapping_passed = mapping_cases
    if not mapping_cases and mapping_report_path.is_file():
        mapping_report = MappingSyntaxCheckAggregateReport.model_validate_json(
            mapping_report_path.read_text()
        )
        mapping_passed = mapping_report.status == "passed" and mapping_report.p12_submission_allowed
    current_commit, current_dirty = git_state(root)
    dirty_paths = git_dirty_paths(root)
    generated_prefixes = (
        "results/backend/",
        "results/qir/",
        "results/nexus/",
        "results/manifests/",
    )
    dirty_generated_only = bool(dirty_paths) and all(
        path.startswith(generated_prefixes) for path in dirty_paths
    )
    actual_hash = sha256_file(qir_path) if qir_path.is_file() else ""

    def authorize(confirmed: bool) -> None:
        assert_nexus_syntax_check_allowed(
            submit_syntax_check=submit_syntax_check,
            environment=os.environ,
            target=target,
            target_classification=target_type,
            authenticated_discovery=discovery.authenticated_access,
            discovered_targets=discovered,
            qir_validation_passed=validation.status == "passed",
            logical_to_qir_mapping_verified=validation.logical_to_qir_mapping_verified,
            expected_qir_hash=export.qir_sha256,
            actual_qir_hash=actual_hash,
            validation_qir_hash=validation.input_sha256,
            artifact_git_commit=export.git_commit,
            current_git_commit=current_commit,
            artifact_git_dirty=export.git_dirty,
            current_git_dirty=current_dirty,
            current_dirty_is_generated_artifacts_only=dirty_generated_only,
            mapping_syntax_checks_passed=mapping_passed,
            interactive_confirmed=confirmed,
        )

    try:
        # Validate every noninteractive condition before showing a confirmation prompt.
        authorize(True)
        confirmed = typer.confirm(
            "This operation uploads a QIR artifact and starts a free Nexus syntax-check job "
            "on Helios-1SC. It must not execute on hardware or an emulator. Continue?"
        )
        authorize(confirmed)
    except NexusSyntaxCheckBlocked as exc:
        write_blocked_syntax_report(
            root,
            target=target,
            target_classification=target_type,
            qir_hash=actual_hash,
            source_hash=export.source_qasm_sha256,
            diagnostic=str(exc),
        )
        console.print(str(exc))
        raise typer.Exit(1) from exc
    project_name = str(settings.nexus.get("project_name", "p12-helios-recovery"))
    timeout = float(settings.nexus.get("timeout_seconds", 1800))
    if mapping_cases:
        mapping_result = submit_mapping_syntax_checks(
            root,
            project_name=project_name,
            timeout_seconds=timeout,
            case_filter=mapping_case,
        )
        console.print(f"Mapping syntax checks: {mapping_result.status}")
        exit_status = 0 if mapping_result.status == "passed" else 1
    else:
        try:
            syntax_result = submit_validated_syntax_check(
                root,
                qir_path=qir_path,
                export=export,
                project_name=project_name,
                timeout_seconds=timeout,
                output_directory=root / "results/nexus/syntax_check/p12",
            )
        except Exception as exc:
            diagnostic = sanitize_diagnostic(exc)
            syntax_result = write_failed_syntax_report(
                root,
                qir_hash=export.qir_bitcode_sha256,
                source_hash=export.source_qasm_sha256,
                diagnostic=diagnostic,
            )
        update_mapping_aggregate_with_p12(root, syntax_result.status)
        console.print(f"P12 syntax check: {syntax_result.status}")
        exit_status = 0 if syntax_result.status == "passed" else 1
    write_manifest(
        root,
        command="nexus-syntax-check",
        arguments=sys.argv[1:],
        start=start,
        exit_status=exit_status,
        inputs=[qir_path, config_path],
        outputs=[root / "results/nexus/syntax_check"],
        config=config_path,
        backend_mode="nexus_syntax_checker_only",
        credentials_detected=True,
    )
    if exit_status:
        raise typer.Exit(exit_status)


@app.command(name="estimate-cost")
def estimate_cost(
    target: Annotated[str, typer.Option("--target")],
    shots: Annotated[str, typer.Option("--shots")] = "20,100,250,500,1000,2000",
) -> None:
    """Record provider-supported cost evidence or an explicit unsupported result."""
    root, start = _root(), datetime.now(UTC)
    shot_values = [int(value.strip()) for value in shots.split(",") if value.strip()]
    report = estimate_costs(root, target, shot_values)
    output = root / "results/cost/cost_estimate.json"
    write_manifest(
        root,
        command="estimate-cost",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0,
        outputs=[output, root / "results/cost/cost_estimate.md"],
        backend_mode="cost_estimation_only",
    )
    console.print(f"Cost estimation status: {report.status}")


@app.command(name="nexus-cost")
def nexus_cost_command(
    target: Annotated[str, typer.Option("--target")] = "Helios-1E",
    qir: Annotated[Path | None, typer.Option("--qir")] = None,
    artifact: Annotated[Path | None, typer.Option("--artifact")] = None,
    mapping_cases: Annotated[bool, typer.Option("--mapping-cases")] = False,
    shots: Annotated[str, typer.Option("--shots")] = "1",
) -> None:
    """Create provider-supported QIR cost-confidence evidence for Helios-1E."""
    root, start = _root(), datetime.now(UTC)
    if target != "Helios-1E":
        raise typer.BadParameter("Cost evidence is restricted to exact target Helios-1E")
    discovery = discover_quantinuum_report()
    descriptor = next(
        (
            device
            for device in discovery.devices
            if device.provider_api == "nexus" and device.device_name == target
        ),
        None,
    )
    if (
        not discovery.authenticated_access
        or descriptor is None
        or descriptor.target_type != "emulator"
    ):
        raise typer.BadParameter(
            "Authenticated Nexus discovery must classify Helios-1E as emulator"
        )
    shot_values = [int(value.strip()) for value in shots.split(",") if value.strip()]
    if mapping_cases:
        if qir is not None or artifact is not None:
            raise typer.BadParameter("--mapping-cases cannot be combined with --qir/--artifact")
        programs = mapping_cost_programs(root)
    else:
        selected = qir or artifact or Path("results/qir/p12.ll")
        selected = selected if selected.is_absolute() else root / selected
        programs = p12_cost_program(root, selected)
    report = estimate_nexus_qir_costs(root, target=target, programs=programs, shots=shot_values)
    output = write_nexus_cost_report(root, report, mapping_cases=mapping_cases)
    write_manifest(
        root,
        command="nexus-cost",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0 if report.status == "supported" else 1,
        outputs=[output, root / "results/nexus/cost/cost_report.md"],
        backend_mode="nexus_remote_costing_job",
        credentials_detected=True,
    )
    console.print(f"Nexus cost evidence: {report.status} ({len(report.items)} estimates)")
    if report.status != "supported":
        raise typer.Exit(1)


@app.command(name="emulator-mapping-check")
def emulator_mapping_check_command(
    target: Annotated[str, typer.Option("--target")] = "Helios-1E",
    mapping_case: Annotated[str | None, typer.Option("--mapping-case")] = None,
    shots: Annotated[int, typer.Option("--shots", min=1)] = 3,
    max_cost: Annotated[float | None, typer.Option("--max-cost")] = None,
    execute_emulator: Annotated[bool, typer.Option("--execute-emulator")] = False,
    config: Annotated[Path, typer.Option("--config")] = Path(
        "configs/helios_emulator_mapping.yaml"
    ),
) -> None:
    """Cost-capped deterministic output-layout validation on Helios-1E only."""
    root, start = _root(), datetime.now(UTC)
    if mapping_case is not None and mapping_case not in MAPPING_CASE_ORDER:
        raise typer.BadParameter(f"Unknown mapping case: {mapping_case}")
    config_path = config if config.is_absolute() else root / config
    settings = yaml.safe_load(config_path.read_text())
    threshold = float(settings["mapping"]["minimum_majority_fraction"])
    discovery = discover_quantinuum_report()
    nexus_devices = [device for device in discovery.devices if device.provider_api == "nexus"]
    descriptor = next((device for device in nexus_devices if device.device_name == target), None)
    target_type = descriptor.target_type if descriptor else "unknown"
    discovered = {device.device_name for device in nexus_devices if device.device_name}
    syntax = MappingSyntaxCheckAggregateReport.model_validate_json(
        (root / "results/nexus/syntax_check/mapping_cases_report.json").read_text()
    )
    syntax_passed = syntax.status == "passed" and syntax.all_mapping_qir_syntax_checks == "passed"
    cost_path = root / "results/nexus/cost/mapping_cases_cost.json"
    cost = (
        NexusCostReport.model_validate_json(cost_path.read_text()) if cost_path.is_file() else None
    )
    selected = [mapping_case] if mapping_case else MAPPING_CASE_ORDER
    cost_evidence = bool(
        cost
        and cost.status == "supported"
        and all(
            any(item.program_name == name and item.shots == shots for item in cost.items)
            for name in selected
        )
    )
    programs = {name: (path, expected) for name, path, expected in mapping_cost_programs(root)}
    hashes_match = all(sha256_file(programs[name][0]) == programs[name][1] for name in selected)

    def authorize(confirmed: bool) -> None:
        assert_helios_emulator_execution_allowed(
            execute_emulator=execute_emulator,
            environment=os.environ,
            target=target,
            target_classification=target_type,
            authenticated_discovery=discovery.authenticated_access,
            discovered_targets=discovered,
            mapping_syntax_checks_passed=syntax_passed,
            p12_syntax_check_passed=True,
            cost_evidence_exists=cost_evidence,
            max_cost=max_cost,
            expected_bitcode_hash="mapping-artifacts-verified",
            actual_bitcode_hash="mapping-artifacts-verified" if hashes_match else "mismatch",
            mapping_validation_passed=False,
            is_p12_pilot=False,
            interactive_confirmed=confirmed,
        )

    try:
        authorize(True)
        confirmed = typer.confirm(
            "This operation starts a paid or quota-consuming emulator job on Helios-1E. "
            "It will not execute on physical hardware. The specified max_cost is a strict "
            "spending ceiling. Continue?"
        )
        authorize(confirmed)
    except HeliosEmulatorExecutionBlocked as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc
    assert max_cost is not None
    report = execute_mapping_cases(
        root,
        target=target,
        shots=shots,
        max_cost=max_cost,
        case_filter=mapping_case,
        minimum_majority_fraction=threshold,
    )
    write_manifest(
        root,
        command="emulator-mapping-check",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0 if report.status in {"passed", "incomplete"} else 1,
        outputs=[root / "results/nexus/emulator_mapping", root / "data/provider_raw/mapping"],
        config=config_path,
        backend_mode="cost_capped_helios_1e_emulator",
        credentials_detected=True,
    )
    console.print(
        f"Emulator mapping: {report.status}; resolved {report.resolved_positions}/98 positions"
    )
    if report.status == "failed":
        raise typer.Exit(1)


@app.command(name="p12-emulator-pilot")
def p12_emulator_pilot_command(
    target: Annotated[str, typer.Option("--target")] = "Helios-1E",
    shots: Annotated[int, typer.Option("--shots", min=1, max=20)] = 10,
    max_cost: Annotated[float | None, typer.Option("--max-cost")] = None,
    execute_emulator: Annotated[bool, typer.Option("--execute-emulator")] = False,
) -> None:
    """Run an optional, blinded, at-most-20-shot P12 pipeline pilot on Helios-1E."""
    root, start = _root(), datetime.now(UTC)
    discovery = discover_quantinuum_report()
    nexus_devices = [device for device in discovery.devices if device.provider_api == "nexus"]
    descriptor = next((device for device in nexus_devices if device.device_name == target), None)
    discovered = {device.device_name for device in nexus_devices if device.device_name}
    mapping_syntax = MappingSyntaxCheckAggregateReport.model_validate_json(
        (root / "results/nexus/syntax_check/mapping_cases_report.json").read_text()
    )
    p12_syntax = NexusSyntaxCheckReport.model_validate_json(
        (root / "results/nexus/syntax_check/p12/syntax_check_report.json").read_text()
    )
    mapping = EmulatorMappingAggregateReport.model_validate_json(
        (root / "results/nexus/emulator_mapping/emulator_mapping_report.json").read_text()
    )
    cost_path = root / "results/nexus/cost/p12_cost.json"
    cost = (
        NexusCostReport.model_validate_json(cost_path.read_text()) if cost_path.is_file() else None
    )
    cost_evidence = bool(
        cost
        and cost.status == "supported"
        and any(item.program_name == "p12" and item.shots == shots for item in cost.items)
    )
    export = QIRExportReport.model_validate_json(
        (root / "results/qir/qir_export_report.json").read_text()
    )
    actual_hash = sha256_file(root / export.qir_bitcode_path)

    def authorize(confirmed: bool) -> None:
        assert_helios_emulator_execution_allowed(
            execute_emulator=execute_emulator,
            environment=os.environ,
            target=target,
            target_classification=descriptor.target_type if descriptor else "unknown",
            authenticated_discovery=discovery.authenticated_access,
            discovered_targets=discovered,
            mapping_syntax_checks_passed=(mapping_syntax.status == "passed"),
            p12_syntax_check_passed=(p12_syntax.status == "passed"),
            cost_evidence_exists=cost_evidence,
            max_cost=max_cost,
            expected_bitcode_hash=export.qir_bitcode_sha256,
            actual_bitcode_hash=actual_hash,
            mapping_validation_passed=(mapping.status == "passed"),
            is_p12_pilot=True,
            interactive_confirmed=confirmed,
        )

    try:
        authorize(True)
        confirmed = typer.confirm(
            "This operation starts a paid or quota-consuming P12 emulator pilot on Helios-1E. "
            "It will not execute on physical hardware, will use at most 20 shots, and max_cost "
            "is a strict spending ceiling. Continue?"
        )
        authorize(confirmed)
    except HeliosEmulatorExecutionBlocked as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc
    assert max_cost is not None
    report = execute_p12_pilot(root, target=target, shots=shots, max_cost=max_cost)
    write_manifest(
        root,
        command="p12-emulator-pilot",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0 if report.status == "passed" else 1,
        outputs=[root / "results/nexus/p12_emulator", root / "data/canonical/p12_emulator"],
        backend_mode="blinded_cost_capped_helios_1e_pilot",
        credentials_detected=True,
    )
    if report.status == "failed":
        console.print(
            f"P12 emulator pilot failed at {report.failure_stage}; job={report.job_ref}; "
            f"reported_cost_hqcs={report.reported_cost_hqcs}. "
            "Diagnostics were preserved; hidden target scored: false"
        )
        raise typer.Exit(1)
    console.print(f"P12 emulator pilot: {report.status}; hidden target scored: false")


@app.command(name="freeze-protocol")
def freeze_protocol_command(
    config: Annotated[Path, typer.Option("--config")] = Path("configs/experiment.yaml"),
) -> None:
    """Freeze only a clean, fully evidenced protocol."""
    root = _root()
    path = config if config.is_absolute() else root / config
    try:
        record = freeze_protocol(root, path)
    except ProtocolFreezeBlocked as exc:
        console.print(f"Protocol freeze blocked: {exc}")
        raise typer.Exit(1) from exc
    console.print(f"Protocol frozen: {record.protocol_hash}")


@app.command(name="public-audit")
def public_audit() -> None:
    """Audit repository release safety without changing visibility."""
    root, start = _root(), datetime.now(UTC)
    report = run_public_audit(root)
    output = root / "results/public_audit.json"
    write_manifest(
        root,
        command="public-audit",
        arguments=sys.argv[1:],
        start=start,
        exit_status=0 if report.passed else 1,
        outputs=[output, root / "results/public_audit.md"],
    )
    console.print(f"Public audit passed: {report.passed}")
    if not report.passed:
        raise typer.Exit(1)


@app.command(name="hardware-smoke-test")
def hardware_smoke_test() -> None:
    """Explicit non-implementation marker for paid execution."""
    console.print("Milestone 3 has no paid hardware execution implementation.")
    raise typer.Exit(1)


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "inspection_report.schema.json": CircuitInspectionReport,
    "compilation_report.schema.json": CompilationReport,
    "run_manifest.schema.json": RunManifest,
    "recovery_report.schema.json": RecoveryReport,
    "available_devices_report.schema.json": AvailableDevicesReport,
    "provider_raw_result.schema.json": ProviderRawResult,
    "canonical_result.schema.json": CanonicalResult,
    "mapping_validation_report.schema.json": MappingValidationReport,
    "qir_export_report.schema.json": QIRExportReport,
    "qir_validation_report.schema.json": QIRValidationReport,
    "qir_output_mapping.schema.json": QIROutputMapping,
    "qir_mapping_cases_report.schema.json": QIRMappingCasesReport,
    "nexus_syntax_check_job.schema.json": NexusSyntaxCheckJob,
    "nexus_syntax_check_report.schema.json": NexusSyntaxCheckReport,
    "mapping_syntax_check_aggregate_report.schema.json": MappingSyntaxCheckAggregateReport,
    "cost_estimate_report.schema.json": CostEstimateReport,
    "nexus_cost_report.schema.json": NexusCostReport,
    "emulator_job_report.schema.json": EmulatorMappingAggregateReport,
    "raw_provider_result_report.schema.json": RawProviderResultReport,
    "provider_output_mapping_report.schema.json": ProviderOutputMappingReport,
    "emulator_mapping_aggregate_report.schema.json": EmulatorMappingAggregateReport,
    "p12_emulator_pilot_report.schema.json": P12EmulatorPilotReport,
    "emulator_authorization_evidence.schema.json": EmulatorAuthorizationEvidence,
    "protocol_freeze_record.schema.json": ProtocolFreezeRecord,
    "readiness_evidence_report.schema.json": ReadinessEvidenceReport,
    "public_audit_report.schema.json": PublicAuditReport,
}


@app.command()
def schemas(check: Annotated[bool, typer.Option("--check")] = False) -> None:
    """Generate or verify Pydantic JSON Schemas."""
    root = _root()
    mismatches = []
    for filename, model in SCHEMA_MODELS.items():
        path = root / "schemas" / filename
        rendered = json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"
        if check:
            if not path.is_file() or path.read_text() != rendered:
                mismatches.append(filename)
        else:
            path.write_text(rendered)
    if mismatches:
        console.print(f"Schema mismatch: {', '.join(mismatches)}")
        raise typer.Exit(1)
    console.print("Schemas are consistent" if check else "Schemas generated")


if __name__ == "__main__":
    app()
