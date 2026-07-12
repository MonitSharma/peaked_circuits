from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast

import typer
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
from .benchmark import run_synthetic_benchmark
from .circuit_inspection import inspect_circuit
from .compilation import compile_from_config, validate_existing
from .config import load_model
from .constants import DEFAULT_QASM
from .cost_estimation import estimate_costs
from .counts_io import load_aggregated_counts
from .hashing import read_sha256sums, sha256_file
from .mapping_validation import run_mapping_validation
from .models import (
    AvailableDevicesReport,
    CanonicalResult,
    CircuitInspectionReport,
    CompilationReport,
    CostEstimateReport,
    MappingSyntaxCheckAggregateReport,
    MappingValidationReport,
    MeasurementMapping,
    NexusSyntaxCheckConfig,
    NexusSyntaxCheckJob,
    NexusSyntaxCheckReport,
    ProtocolFreezeRecord,
    ProviderRawResult,
    PublicAuditReport,
    QIRExportReport,
    QIRMappingCasesReport,
    QIROutputMapping,
    QIRValidationReport,
    ReadinessEvidenceReport,
    RecoveryReport,
    RunManifest,
    SyntheticExperimentConfig,
)
from .nexus_syntax_check import (
    submit_mapping_syntax_checks,
    submit_validated_syntax_check,
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
            )
        except Exception as exc:
            diagnostic = sanitize_diagnostic(exc)
            syntax_result = write_failed_syntax_report(
                root,
                qir_hash=export.qir_bitcode_sha256,
                source_hash=export.source_qasm_sha256,
                diagnostic=diagnostic,
            )
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
