from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .hashing import sha256_file
from .models import NexusCostItem, NexusCostReport, QIRExportReport, QIRMappingCasesReport
from .reporting import package_versions, write_json


def _safe_ref(value: Any) -> str:
    identifier = getattr(value, "id", None)
    return str(identifier if identifier is not None else value)


def estimate_nexus_qir_costs(
    root: Path,
    *,
    target: str,
    programs: list[tuple[str, Path, str]],
    shots: list[int],
    project_name: str = "p12-helios-recovery",
    client_module: Any | None = None,
) -> NexusCostReport:
    if target != "Helios-1E":
        raise ValueError("Nexus cost evidence is restricted to Helios-1E")
    if not programs or not shots or any(value <= 0 for value in shots):
        raise ValueError("At least one program and positive shot count are required")
    expanded = [(name, path, expected, shot) for name, path, expected in programs for shot in shots]
    qnx = client_module or importlib.import_module("qnexus")
    try:
        project = qnx.projects.get_or_create(
            name=project_name,
            description="P12 Helios cost evidence and cost-capped emulator validation",
        )
        refs = []
        for name, path, expected, shot in expanded:
            if sha256_file(path) != expected:
                raise RuntimeError(f"Frozen bitcode hash mismatch for {name}")
            refs.append(
                qnx.qir.upload(
                    qir=path.read_bytes(),
                    name=f"cost-{name}-{expected[:12]}-{shot}",
                    project=project,
                    description="QIR upload for provider cost-confidence evidence",
                )
            )
        estimates = qnx.qir.cost_confidence(
            programs=refs,
            n_shots=[item[3] for item in expanded],
            project=project,
            system_name="Helios-1",
        )
        if len(estimates) != len(expanded):
            raise RuntimeError("Provider returned the wrong number of cost estimates")
        now = datetime.now(UTC)
        items = [
            NexusCostItem(
                program_name=name,
                bitcode_sha256=expected,
                target="Helios-1E",
                shots=shot,
                estimated_hqcs=float(estimate),
                confidence=float(confidence),
                provider_timestamp=now,
            )
            for (name, _path, expected, shot), (estimate, confidence) in zip(
                expanded, estimates, strict=True
            )
        ]
        return NexusCostReport(
            status="supported",
            target=target,
            items=items,
            api_used="qnexus.qir.cost_confidence",
            remote_costing_job_created=True,
            diagnostics=[
                "qnexus 0.46 cost_confidence creates a remote costing job but returns only "
                "(estimate, confidence) tuples; its job reference is not exposed by this API."
            ],
            package_versions=package_versions(),
            input_hashes={
                path.relative_to(root).as_posix(): expected for _, path, expected in programs
            },
        )
    except Exception as exc:
        return NexusCostReport(
            status="failed",
            target=target,
            items=[],
            api_used="qnexus.qir.cost_confidence",
            remote_costing_job_created=False,
            diagnostics=[f"{type(exc).__name__}: {exc}"],
            package_versions=package_versions(),
        )


def mapping_cost_programs(root: Path) -> list[tuple[str, Path, str]]:
    report = QIRMappingCasesReport.model_validate_json(
        (root / "results/qir/mapping_cases/mapping_qir_export_report.json").read_text()
    )
    programs: list[tuple[str, Path, str]] = []
    for case in report.cases:
        export = QIRExportReport.model_validate_json((root / case.export_report_path).read_text())
        programs.append((case.case_name, root / export.qir_bitcode_path, export.qir_bitcode_sha256))
    return programs


def p12_cost_program(root: Path, qir_path: Path) -> list[tuple[str, Path, str]]:
    export = QIRExportReport.model_validate_json(
        (qir_path.parent / "qir_export_report.json").read_text()
    )
    return [("p12", root / export.qir_bitcode_path, export.qir_bitcode_sha256)]


def write_nexus_cost_report(root: Path, report: NexusCostReport, *, mapping_cases: bool) -> Path:
    output = root / "results/nexus/cost"
    path = output / ("mapping_cases_cost.json" if mapping_cases else "p12_cost.json")
    write_json(path, report)
    rows = "\n".join(
        f"| {item.program_name} | {item.shots} | {item.estimated_hqcs} | {item.confidence} |"
        for item in report.items
    )
    (output / "cost_report.md").write_text(
        "# Nexus provider cost evidence\n\n"
        "`qnexus.qir.cost_confidence` creates a remote costing job. It is not described as free; "
        "the returned API value contains estimates and confidence but no job reference.\n\n"
        "| Program | Shots | Estimated HQC | Confidence |\n|---|---:|---:|---:|\n" + rows + "\n"
    )
    return path
