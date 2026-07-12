from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from .bit_ordering import raw_bitstring_to_canonical
from .hardware_guard import HardwareSubmissionBlocked, assert_hardware_submission_allowed
from .hashing import read_sha256sums, sha256_file
from .models import (
    CompilationReport,
    HardwareReadinessReport,
    MappingSyntaxCheckAggregateReport,
    MappingValidationReport,
    MeasurementMapping,
    NexusSyntaxCheckReport,
    QIRExportReport,
    QIRMappingCasesReport,
    QIRValidationReport,
    ReadinessEvidence,
    ReadinessEvidenceReport,
    ReadinessState,
)
from .qasm_io import load_qasm
from .reporting import git_state, package_versions, write_json


def _fixture_checks(root: Path) -> bool:
    fixture = load_qasm(root / "circuits/fixtures/small_random.qasm")
    if fixture.sdk_circuit is None:
        return False
    state = fixture.sdk_circuit.get_statevector()
    normalized = bool(np.isclose(np.vdot(state, state), 1.0))
    mapped = raw_bitstring_to_canonical(
        "00001",
        logical_to_classical={i: i for i in range(5)},
        sdk_string_order="msb_left",
        register_layout=[{"name": "c", "classical_indices": list(range(5))}],
    )
    return normalized and mapped == "10000"


def _hardware_guard_self_check() -> bool:
    try:
        assert_hardware_submission_allowed(
            execute_hardware=True,
            environment={
                "P12_ENABLE_HARDWARE": "1",
                "P12_CONFIRM_PAID_EXECUTION": "I_UNDERSTAND_THIS_MAY_CONSUME_HQC",
            },
            readiness_passed=True,
            device_is_physical=True,
            backend_mode="execute",
            interactive_confirmed=True,
        )
    except HardwareSubmissionBlocked:
        return True
    return False


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _evidence(
    root: Path, check: str, passed: bool, path: Path | None, details: str
) -> ReadinessEvidence:
    return ReadinessEvidence(
        check=check,
        passed=passed,
        evidence_path=path.relative_to(root).as_posix() if path and path.exists() else None,
        evidence_hash=sha256_file(path) if path and path.is_file() else None,
        details=details,
    )


def _commit_tagged(root: Path, commit: str | None) -> bool:
    if not commit:
        return False
    try:
        return bool(
            subprocess.run(
                ["git", "tag", "--points-at", commit],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return False


def readiness_state_from_checks(checks: dict[str, bool | None], *, offline: bool) -> ReadinessState:
    if checks.get("mapping_case_syntax_checks_passed") and checks.get("p12_syntax_check_passed"):
        return ReadinessState.READY_FOR_EMULATOR_MAPPING_VALIDATION
    if all(
        checks.get(name) is True
        for name in (
            "qir_export_completed",
            "qir_hash_recorded",
            "qir_structural_validation_passed",
            "logical_to_qir_mapping_complete",
            "mapping_case_qir_exports_passed",
        )
    ):
        return ReadinessState.READY_FOR_SYNTAX_CHECK
    if checks.get("qir_export_completed") and checks.get("qir_hash_recorded"):
        return ReadinessState.READY_FOR_QIR_EXPORT
    if checks.get("compiler_version_frozen"):
        return ReadinessState.READY_FOR_COMPILE_ONLY
    if offline:
        return ReadinessState.READY_FOR_OFFLINE_ANALYSIS
    return ReadinessState.NOT_READY


def build_readiness(root: Path) -> HardwareReadinessReport:
    qasm = root / "circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm"
    sums = qasm.parent / "SHA256SUMS"
    compilation_path = root / "results/compilation/compilation_report.json"
    mapping_path = root / "results/compilation/measurement_mapping.json"
    mapping_validation_path = root / "results/mapping_validation/mapping_validation_report.json"
    synthetic_path = root / "results/synthetic/synthetic_report.json"
    cost_path = root / "results/cost/cost_estimate.json"
    protocol_path = root / "results/protocol/protocol_freeze.json"
    qir_export_path = root / "results/qir/qir_export_report.json"
    qir_validation_path = root / "results/qir/qir_validation_report.json"
    qir_mapping_path = root / "results/qir/qir_output_mapping.json"
    mapping_qir_path = root / "results/qir/mapping_cases/mapping_qir_export_report.json"
    mapping_syntax_path = root / "results/nexus/syntax_check/mapping_cases_report.json"
    p12_syntax_path = root / "results/nexus/syntax_check/syntax_check_report.json"
    compilation: CompilationReport | None = None
    if compilation_path.is_file():
        try:
            compilation = CompilationReport.model_validate_json(compilation_path.read_text())
        except Exception:
            compilation = None
    mapping: MeasurementMapping | None = None
    if mapping_path.is_file():
        try:
            mapping = MeasurementMapping.model_validate_json(mapping_path.read_text())
        except Exception:
            mapping = None
    mapping_validation: MappingValidationReport | None = None
    if mapping_validation_path.is_file():
        try:
            mapping_validation = MappingValidationReport.model_validate_json(
                mapping_validation_path.read_text()
            )
        except Exception:
            mapping_validation = None
    cost = _load_json(cost_path)
    protocol = _load_json(protocol_path)
    try:
        qir_export = QIRExportReport.model_validate_json(qir_export_path.read_text())
    except Exception:
        qir_export = None
    try:
        qir_validation = QIRValidationReport.model_validate_json(qir_validation_path.read_text())
    except Exception:
        qir_validation = None
    try:
        qir_mapping = _load_json(qir_mapping_path)
    except Exception:
        qir_mapping = {}
    try:
        mapping_qir = QIRMappingCasesReport.model_validate_json(mapping_qir_path.read_text())
    except Exception:
        mapping_qir = None
    try:
        mapping_syntax = MappingSyntaxCheckAggregateReport.model_validate_json(
            mapping_syntax_path.read_text()
        )
    except Exception:
        mapping_syntax = None
    try:
        p12_syntax = NexusSyntaxCheckReport.model_validate_json(p12_syntax_path.read_text())
    except Exception:
        p12_syntax = None
    source_frozen = (
        qasm.is_file()
        and sums.is_file()
        and read_sha256sums(sums).get(qasm.name) == sha256_file(qasm)
    )
    commit, _ = git_state(root)
    checks = {
        "source_hash_frozen": source_frozen,
        "compiler_version_frozen": bool(compilation and compilation.package_versions.get("pytket")),
        "backend_identified": bool(compilation and compilation.backend.device_name),
        "backend_has_98_qubits": bool(compilation and compilation.backend.has_at_least_98_qubits),
        "target_validity_passed": bool(
            compilation and compilation.validation and compilation.validation.passed
        ),
        "compiled_circuit_hash_recorded": bool(
            compilation and compilation.compiled and compilation.compiled.get("compiled_qasm_hash")
        ),
        "logical_permutation_resolved": bool(
            compilation
            and compilation.unknown_permutation_count == 0
            and compilation.mapping_complete
        ),
        "measurement_mapping_complete": bool(
            mapping and mapping.complete and len(mapping.entries) == 98
        ),
        "mapping_validation_passed": bool(
            mapping_validation
            and mapping_validation.status == "passed"
            and mapping_validation.passed_cases == mapping_validation.total_cases == 6
        ),
        "synthetic_tests_passed": synthetic_path.is_file(),
        "fixture_semantic_tests_passed": _fixture_checks(root),
        "cost_estimate_obtained": cost.get("status") == "supported",
        "shot_protocol_frozen": protocol.get("status") == "frozen",
        "recovery_method_frozen": protocol.get("status") == "frozen"
        and bool(protocol.get("configuration", {}).get("primary_analysis", {}).get("method")),
        "tracker_protocol_confirmed": bool(
            protocol.get("configuration", {}).get("tracker_protocol_confirmed")
        ),
        "repository_commit_recorded": bool(compilation and compilation.git_commit),
        "repository_commit_tagged": _commit_tagged(root, commit),
        "hardware_guard_tests_passed": _hardware_guard_self_check(),
        "qir_export_completed": bool(qir_export and qir_export.status == "success"),
        "qir_hash_recorded": bool(
            qir_export
            and qir_export.qir_sha256
            and qir_export.qir_bitcode_sha256
            and (root / qir_export.qir_path).is_file()
            and sha256_file(root / qir_export.qir_path) == qir_export.qir_sha256
            and (root / qir_export.qir_bitcode_path).is_file()
            and sha256_file(root / qir_export.qir_bitcode_path) == qir_export.qir_bitcode_sha256
        ),
        "qir_structural_validation_passed": bool(
            qir_validation and qir_validation.status == "passed"
        ),
        "logical_to_qir_mapping_complete": bool(
            qir_export
            and qir_export.logical_to_qir_mapping_verified
            and qir_mapping.get("logical_to_qir_mapping_verified") is True
            and len(qir_mapping.get("entries", [])) == 98
        ),
        "mapping_case_qir_exports_passed": bool(
            mapping_qir
            and mapping_qir.status == "passed"
            and mapping_qir.passed_cases == mapping_qir.total_cases == 6
        ),
        "mapping_case_syntax_checks_passed": bool(
            mapping_syntax
            and mapping_syntax.status == "passed"
            and mapping_syntax.all_mapping_qir_syntax_checks == "passed"
        ),
        "p12_syntax_check_passed": bool(p12_syntax and p12_syntax.status == "passed"),
        "provider_result_order_verified": False,
        "emulator_mapping_validation_passed": False,
    }
    evidence_paths: dict[str, Path | None] = {
        "source_hash_frozen": sums,
        "compiler_version_frozen": compilation_path,
        "backend_identified": compilation_path,
        "backend_has_98_qubits": compilation_path,
        "target_validity_passed": compilation_path,
        "compiled_circuit_hash_recorded": compilation_path,
        "logical_permutation_resolved": compilation_path,
        "measurement_mapping_complete": mapping_path,
        "mapping_validation_passed": mapping_validation_path,
        "synthetic_tests_passed": synthetic_path,
        "fixture_semantic_tests_passed": root / "tests/test_qasm_io.py",
        "cost_estimate_obtained": cost_path,
        "shot_protocol_frozen": protocol_path,
        "recovery_method_frozen": protocol_path,
        "tracker_protocol_confirmed": protocol_path,
        "repository_commit_recorded": compilation_path,
        "repository_commit_tagged": root / ".git/refs/tags",
        "hardware_guard_tests_passed": root / "tests/test_hardware_guard.py",
        "qir_export_completed": qir_export_path,
        "qir_hash_recorded": qir_export_path,
        "qir_structural_validation_passed": qir_validation_path,
        "logical_to_qir_mapping_complete": qir_mapping_path,
        "mapping_case_qir_exports_passed": mapping_qir_path,
        "mapping_case_syntax_checks_passed": mapping_syntax_path,
        "p12_syntax_check_passed": p12_syntax_path,
        "provider_result_order_verified": None,
        "emulator_mapping_validation_passed": None,
    }
    evidence = [
        _evidence(
            root,
            name,
            passed,
            evidence_paths[name],
            "Evidence present and valid" if passed else "Missing or failing prerequisite",
        )
        for name, passed in checks.items()
    ]
    offline = all(
        checks[name]
        for name in (
            "source_hash_frozen",
            "synthetic_tests_passed",
            "fixture_semantic_tests_passed",
            "hardware_guard_tests_passed",
        )
    )
    state = readiness_state_from_checks(checks, offline=offline)
    blockers = [name for name, passed in checks.items() if not passed]
    report = HardwareReadinessReport(
        ready=False,
        state=state.value,
        checks=checks,
        blockers=blockers,
        evidence=evidence,
        package_versions=package_versions(),
        input_hashes={qasm.relative_to(root).as_posix(): sha256_file(qasm)}
        if qasm.is_file()
        else {},
    )
    write_json(root / "results/hardware_readiness_report.json", report)
    write_json(
        root / "results/readiness_evidence.json",
        ReadinessEvidenceReport(
            state=state, evidence=evidence, blockers=blockers, package_versions=package_versions()
        ),
    )
    markdown = f"# Hardware readiness\n\nState: **{state.value}**\n\n"
    markdown += "\n".join(f"- [{'x' if passed else ' '}] {name}" for name, passed in checks.items())
    markdown += (
        "\n\nMilestone 3 stops before emulator or hardware execution. Provider result order "
        "remains unresolved.\n"
    )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs/hardware_readiness.md").write_text(markdown)
    return report
