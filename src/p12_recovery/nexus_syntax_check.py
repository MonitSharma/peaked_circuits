from __future__ import annotations

import importlib
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

try:
    import qnexus as qnx
except ImportError:
    qnx = None  # type: ignore

from .backends.quantinuum import sanitize_diagnostic
from .hashing import sha256_file
from .models import (
    MappingSyntaxCheckAggregateReport,
    NexusSyntaxCheckJob,
    NexusSyntaxCheckReport,
    QIRExportReport,
    QIRMappingCasesReport,
)
from .qir_validation import validate_qir_artifact
from .reporting import package_versions, write_json


class SyntaxCheckStage(StrEnum):
    AUTHORIZATION = "authorization"
    TARGET_DISCOVERY = "target_discovery"
    PROJECT_RESOLUTION = "project_resolution"
    QIR_UPLOAD = "qir_upload"
    JOB_CREATION = "job_creation"
    JOB_WAIT = "job_wait"
    REMOTE_SYNTAX_CHECK = "remote_syntax_check"
    RESULT_RETRIEVAL = "result_retrieval"


class NexusSyntaxCheckFailure(Exception):
    def __init__(
        self,
        stage: SyntaxCheckStage,
        exc: Exception,
        qir_uploaded: bool = False,
        job_created: bool = False,
    ):
        self.stage = stage
        self.exc = exc
        self.qir_uploaded = qir_uploaded
        self.job_created = job_created
        super().__init__(str(exc))


def create_syntax_check_job(
    *,
    qir_ref: Any,
    backend_config: Any,
    project_ref: Any,
    job_name: str,
    client_module: Any = None,
) -> Any:
    local_qnx = client_module if client_module is not None else qnx
    if local_qnx is None:
        raise ImportError("qnexus package is required for starting execute job.")
    return local_qnx.start_execute_job(
        programs=[qir_ref],
        n_shots=[1],
        backend_config=backend_config,
        project=project_ref,
        name=job_name,
    )

MAPPING_CASE_ORDER = [
    "all_zeros",
    "q0",
    "q97",
    "q0_q7_q31_q64_q97",
    "non_palindromic_blocks",
    "alternating_q0_one",
]


def _safe_ref(value: Any) -> str:
    identifier = getattr(value, "id", None)
    return str(identifier if identifier is not None else value)


def _safe_status(value: Any) -> str:
    status = getattr(value, "status", value)
    enum_value = getattr(status, "value", status)
    return str(enum_value)


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def submit_validated_syntax_check(
    root: Path,
    *,
    qir_path: Path,
    export: QIRExportReport,
    project_name: str,
    timeout_seconds: float,
    client_module: Any | None = None,
    output_directory: Path | None = None,
) -> NexusSyntaxCheckReport:
    """Upload bitcode and submit only to Helios-1SC after an external guard passes."""
    qir_path = qir_path.resolve()
    if sha256_file(qir_path) != export.qir_sha256:
        raise RuntimeError("Guarded QIR changed before Nexus upload")
    bitcode_path = root / export.qir_bitcode_path
    if not bitcode_path.is_file() or sha256_file(bitcode_path) != export.qir_bitcode_sha256:
        raise RuntimeError("Guarded QIR bitcode changed before Nexus upload")

    try:
        qnx_client: Any = client_module if client_module is not None else importlib.import_module("qnexus")
    except Exception as exc:
        raise NexusSyntaxCheckFailure(
            stage=SyntaxCheckStage.AUTHORIZATION,
            exc=exc,
            qir_uploaded=False,
            job_created=False,
        ) from exc

    try:
        project = qnx_client.projects.get_or_create(
            name=project_name,
            description="P12 Helios-1SC syntax validation only; no emulator or hardware execution",
        )
    except Exception as exc:
        raise NexusSyntaxCheckFailure(
            stage=SyntaxCheckStage.PROJECT_RESOLUTION,
            exc=exc,
            qir_uploaded=False,
            job_created=False,
        ) from exc

    artifact_name = f"p12-syntax-{qir_path.stem}-{export.qir_bitcode_sha256[:12]}"
    try:
        qir_ref = qnx_client.qir.upload(
            qir=bitcode_path.read_bytes(),
            name=artifact_name,
            project=project,
            description="Locally validated QIR bitcode for Helios-1SC only",
        )
    except Exception as exc:
        raise NexusSyntaxCheckFailure(
            stage=SyntaxCheckStage.QIR_UPLOAD,
            exc=exc,
            qir_uploaded=False,
            job_created=False,
        ) from exc

    try:
        config = qnx_client.models.HeliosConfig(system_name="Helios-1SC")
        submitted = datetime.now(UTC)
        job_ref = create_syntax_check_job(
            qir_ref=qir_ref,
            backend_config=config,
            project_ref=project,
            job_name=artifact_name,
            client_module=qnx_client,
        )
    except Exception as exc:
        raise NexusSyntaxCheckFailure(
            stage=SyntaxCheckStage.JOB_CREATION,
            exc=exc,
            qir_uploaded=True,
            job_created=False,
        ) from exc

    try:
        wait_status = qnx_client.jobs.wait_for(job_ref, timeout=timeout_seconds)
        completed = datetime.now(UTC)
        final_status = _safe_status(wait_status)
    except Exception as exc:
        raise NexusSyntaxCheckFailure(
            stage=SyntaxCheckStage.JOB_WAIT,
            exc=exc,
            qir_uploaded=True,
            job_created=True,
        ) from exc

    try:
        result_refs = list(qnx_client.jobs.results(job_ref, allow_incomplete=True))
        result_ref = result_refs[0] if result_refs else None
        reported_cost = getattr(result_ref, "cost", None) if result_ref is not None else None
    except Exception as exc:
        raise NexusSyntaxCheckFailure(
            stage=SyntaxCheckStage.RESULT_RETRIEVAL,
            exc=exc,
            qir_uploaded=True,
            job_created=True,
        ) from exc

    passed = final_status.upper() == "COMPLETED"
    diagnostics = [] if passed else [f"Nexus terminal status: {final_status}"]
    output = output_directory or root / "results/nexus/syntax_check"
    output.mkdir(parents=True, exist_ok=True)
    job = NexusSyntaxCheckJob(
        project_ref=_safe_ref(project),
        qir_artifact_ref=_safe_ref(qir_ref),
        syntax_check_job_ref=_safe_ref(job_ref),
        target="Helios-1SC",
        target_classification="syntax_checker",
        submission_timestamp=submitted,
        completion_timestamp=completed,
        final_status=final_status,
        submitted_qir_sha256=export.qir_bitcode_sha256,
        source_qasm_sha256=export.source_qasm_sha256,
        reported_cost_hqcs=float(reported_cost) if reported_cost is not None else None,
        package_versions=package_versions(),
        input_hashes={export.qir_bitcode_path: export.qir_bitcode_sha256},
    )
    write_json(output / "job.json", job)
    safe_result = {
        "result_ref": _safe_ref(result_ref) if result_ref is not None else None,
        "final_status": final_status,
        "reported_cost_hqcs": reported_cost,
        "contains_provider_measurements": False,
        "target": "Helios-1SC",
    }
    write_json(output / "result.json", safe_result)
    (output / "diagnostics.txt").write_text("\n".join(diagnostics) + ("\n" if diagnostics else ""))
    (output / "submitted_qir_sha256.txt").write_text(export.qir_bitcode_sha256 + "\n")
    report = NexusSyntaxCheckReport(
        status="passed" if passed else "failed",
        target="Helios-1SC",
        target_classification="syntax_checker",
        qir_sha256=export.qir_bitcode_sha256,
        source_qasm_sha256=export.source_qasm_sha256,
        project_ref=_safe_ref(project),
        qir_artifact_ref=_safe_ref(qir_ref),
        job_ref=_safe_ref(job_ref),
        final_status=final_status,
        diagnostics=diagnostics,
        reported_cost_hqcs=float(reported_cost) if reported_cost is not None else None,
        package_versions=package_versions(),
        input_hashes={export.qir_bitcode_path: export.qir_bitcode_sha256},
    )
    write_json(output / "syntax_check_report.json", report)
    (output / "syntax_check_report.md").write_text(
        "# Nexus Helios-1SC syntax check\n\n"
        f"Status: **{report.status}**  \n"
        f"Target: `{report.target}` (`{report.target_classification}`)  \n"
        f"Submitted bitcode SHA-256: `{report.qir_sha256}`  \n"
        f"Reported prospective cost: `{report.reported_cost_hqcs}` HQC  \n"
        "HQCs used: **false**. Emulator/hardware execution: **false**.\n"
    )
    return report


def submit_mapping_syntax_checks(
    root: Path,
    *,
    project_name: str,
    timeout_seconds: float,
    client_module: Any | None = None,
    case_filter: str | None = None,
) -> MappingSyntaxCheckAggregateReport:
    mapping_report_path = root / "results/qir/mapping_cases/mapping_qir_export_report.json"
    mapping = QIRMappingCasesReport.model_validate_json(mapping_report_path.read_text())
    by_name = {case.case_name: case for case in mapping.cases}

    statuses: dict[str, Any] = {}
    existing_report_path = root / "results/nexus/syntax_check/mapping_cases_report.json"
    if existing_report_path.is_file():
        try:
            existing_report = MappingSyntaxCheckAggregateReport.model_validate_json(
                existing_report_path.read_text()
            )
            statuses.update(existing_report.case_statuses)
        except Exception:
            pass

    for case_name in MAPPING_CASE_ORDER:
        if case_filter is not None and case_name != case_filter:
            if case_name not in statuses:
                statuses[case_name] = "not_submitted"
            continue

        case = by_name[case_name]
        qir_path = root / case.qir_path
        export = QIRExportReport.model_validate_json((root / case.export_report_path).read_text())
        validation = validate_qir_artifact(
            root,
            qir_path,
            export_report_path=root / case.export_report_path,
            write_report=False,
        )
        if validation.status != "passed":
            statuses[case_name] = "local_validation_failed"
            break
        try:
            result = submit_validated_syntax_check(
                root,
                qir_path=qir_path,
                export=export,
                project_name=project_name,
                timeout_seconds=timeout_seconds,
                client_module=client_module,
                output_directory=root
                / "results/nexus/syntax_check/mapping_cases"
                / case_name,
            )
            if result.status == "passed":
                statuses[case_name] = "passed"
            else:
                statuses[case_name] = {
                    "status": "failed",
                    "stage": "remote_syntax_check",
                    "exception_type": "None",
                    "diagnostic": "; ".join(result.diagnostics),
                    "qir_uploaded": True,
                    "job_created": True,
                }
        except NexusSyntaxCheckFailure as exc:
            statuses[case_name] = {
                "status": "failed",
                "stage": exc.stage,
                "exception_type": type(exc.exc).__name__,
                "diagnostic": str(exc.exc),
                "qir_uploaded": exc.qir_uploaded,
                "job_created": exc.job_created,
            }
            failure_dir = root / "results/nexus/syntax_check"
            failure_dir.mkdir(parents=True, exist_ok=True)
            (failure_dir / "diagnostics.txt").write_text(str(exc.exc) + "\n")
            break
        except Exception as exc:
            statuses[case_name] = {
                "status": "failed",
                "stage": "unknown",
                "exception_type": type(exc).__name__,
                "diagnostic": str(exc),
                "qir_uploaded": False,
                "job_created": False,
            }
            failure_dir = root / "results/nexus/syntax_check"
            failure_dir.mkdir(parents=True, exist_ok=True)
            (failure_dir / "diagnostics.txt").write_text(sanitize_diagnostic(exc) + "\n")
            break

        if statuses[case_name] != "passed":
            break

    all_passed = len(statuses) == len(MAPPING_CASE_ORDER) and all(
        (isinstance(status, str) and status == "passed") for status in statuses.values()
    )
    aggregate = MappingSyntaxCheckAggregateReport(
        status="passed" if all_passed else "failed",
        target="Helios-1SC",
        ordered_cases=MAPPING_CASE_ORDER,
        case_statuses=statuses,
        p12_submission_allowed=all_passed,
        local_logical_to_qir_mapping="passed" if mapping.status == "passed" else "failed",
        all_mapping_qir_syntax_checks="passed" if all_passed else "failed",
        p12_qir_syntax_check="not_submitted",
        package_versions=package_versions(),
        input_hashes={case.qir_path: case.qir_sha256 for case in mapping.cases},
    )
    write_json(
        root / "results/nexus/syntax_check/mapping_cases_report.json",
        aggregate,
    )
    return aggregate


def write_blocked_syntax_report(
    root: Path,
    *,
    target: str,
    target_classification: str,
    qir_hash: str,
    source_hash: str,
    diagnostic: str,
) -> NexusSyntaxCheckReport:
    report = NexusSyntaxCheckReport(
        status="blocked",
        target=target,
        target_classification=target_classification,
        qir_sha256=qir_hash,
        source_qasm_sha256=source_hash,
        diagnostics=[diagnostic],
        package_versions=package_versions(),
    )
    output = root / "results/nexus/syntax_check"
    write_json(output / "syntax_check_report.json", report)
    output.mkdir(parents=True, exist_ok=True)
    (output / "diagnostics.txt").write_text(diagnostic + "\n")
    return report


def write_failed_syntax_report(
    root: Path,
    *,
    qir_hash: str,
    source_hash: str,
    diagnostic: str,
) -> NexusSyntaxCheckReport:
    report = NexusSyntaxCheckReport(
        status="failed",
        target="Helios-1SC",
        target_classification="syntax_checker",
        qir_sha256=qir_hash,
        source_qasm_sha256=source_hash,
        diagnostics=[diagnostic],
        package_versions=package_versions(),
    )
    output = root / "results/nexus/syntax_check"
    write_json(output / "syntax_check_report.json", report)
    output.mkdir(parents=True, exist_ok=True)
    (output / "diagnostics.txt").write_text(diagnostic + "\n")
    return report
