from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console

from .acquisition import fetch_source
from .backends.quantinuum import credentials_detected, quantinuum_available
from .benchmark import run_synthetic_benchmark
from .circuit_inspection import inspect_circuit
from .compilation import compile_from_config, validate_existing
from .config import load_model
from .constants import DEFAULT_QASM
from .counts_io import load_aggregated_counts
from .hashing import read_sha256sums, sha256_file
from .models import (
    CircuitInspectionReport,
    CompilationReport,
    RecoveryReport,
    RunManifest,
    SyntheticExperimentConfig,
)
from .readiness import build_readiness
from .recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)
from .reporting import (
    inspection_markdown,
    package_versions,
    save_inspection_figures,
    write_json,
    write_manifest,
)

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
        "qiskit": _version("qiskit"),
        "Credentials detected": credentials_detected(),
        "Configured backend": os.environ.get("P12_QUANTINUUM_DEVICE") or "not configured",
        "Hardware enabled": os.environ.get("P12_ENABLE_HARDWARE") == "1",
        "QASM exists": qasm.is_file(),
        "QASM checksum matches": checksum_ok,
        "Ready for inspection": qasm.is_file() and checksum_ok,
        "Ready for compilation": qasm.is_file() and quantinuum_available(),
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
) -> None:
    """Compile only; this command has no submission capability."""
    root, start = _root(), datetime.now(UTC)
    path = config if config.is_absolute() else root / config
    report = compile_from_config(root, path)
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
    """Build the Milestone 1 hardware-readiness report."""
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
    console.print(f"Hardware ready: {report.ready} (Milestone 1 is always blocked)")


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "inspection_report.schema.json": CircuitInspectionReport,
    "compilation_report.schema.json": CompilationReport,
    "run_manifest.schema.json": RunManifest,
    "recovery_report.schema.json": RecoveryReport,
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
