from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from .circuit_inspection import inspect_circuit
from .hashing import read_sha256sums, sha256_file
from .models import QIRExportReport, QIROutputMapping, QIRValidationReport
from .qir_export import _measurement_pairs, build_qir
from .reporting import package_versions, write_json

_RESOURCE_COUNTS = re.compile(
    r'"required_num_qubits"="(?P<qubits>\d+)".*"required_num_results"="(?P<results>\d+)"'
)
_ABSOLUTE_PATH = re.compile(
    r"(?:/" + r"Users/|/" + r"home/|[A-Za-z]:\\Users\\)"
)
_CREDENTIAL = re.compile(
    r"(?i)(?:bearer\s+[a-z0-9._~-]+|(?:token|secret|password|api[_ -]?key)\s*[:=]\s*\S+|"
    r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b)"
)


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"external:{path.name}"


def _fixture_structural_validation() -> bool:
    """Verify representative fixtures convert and parse; this is not QIR execution."""
    import pyqir
    from pytket import Circuit
    from pytket.qir.conversion.api import QIRFormat, QIRProfile, pytket_to_qir

    fixture_builders: list[tuple[int, list[int], bool]] = [
        (3, [], False),
        (3, [0], False),
        (3, [2], False),
        (5, [0, 3], False),
        (5, [0, 2, 4], False),
        (2, [], True),
    ]
    for width, ones, entangled in fixture_builders:
        circuit = Circuit(width)
        for index in ones:
            circuit.X(index)
        if entangled:
            circuit.H(0).CX(0, 1)
        for index in range(width):
            register = circuit.add_c_register(f"m{index:03d}", 1)
            circuit.Measure(index, register[0])
        rendered = pytket_to_qir(
            circuit,
            name="p12_qir_fixture",
            qir_format=QIRFormat.STRING,
            profile=QIRProfile.BASE,
        )
        if not isinstance(rendered, str):
            return False
        module = pyqir.Module.from_ir(pyqir.Context(), rendered)
        module.verify()
        if set(_measurement_pairs(rendered)) != {(index, index) for index in range(width)}:
            return False
    return True


def _load_export_report(input_path: Path, explicit: Path | None) -> tuple[Path | None, QIRExportReport | None]:
    candidates = [explicit] if explicit else [
        input_path.parent / "qir_export_report.json",
        input_path.parent / "export_report.json",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            try:
                return candidate, QIRExportReport.model_validate_json(candidate.read_text())
            except Exception:
                return candidate, None
    return None, None


def validate_qir_artifact(
    root: Path,
    input_path: Path,
    *,
    export_report_path: Path | None = None,
    write_report: bool = True,
) -> QIRValidationReport:
    input_path = input_path.resolve()
    report_path, export = _load_export_report(input_path, export_report_path)
    text = ""
    input_hash: str | None = None
    diagnostics: list[str] = []
    checks: dict[str, bool] = {
        "file_exists": input_path.is_file(),
        "file_nonempty": False,
        "hash_matches_export": False,
        "llvm_module_parses": False,
        "llvm_module_verifies": False,
        "resource_counts_match": False,
        "measurement_count_matches": False,
        "result_output_count_matches": False,
        "logical_measurement_pairs_complete": False,
        "no_unresolved_non_qir_symbols": False,
        "no_absolute_local_paths": False,
        "no_credential_like_material": False,
        "operation_accounting_matches": False,
        "source_metadata_agrees": False,
        "source_hash_matches_frozen": False,
        "mapping_report_complete": False,
        "bitcode_matches_export": False,
        "reproducible_from_frozen_source": False,
        "fixture_structural_validation_passed": False,
    }
    required_qubits = required_results = measurement_count = result_count = gate_calls = None
    if input_path.is_file():
        data = input_path.read_bytes()
        checks["file_nonempty"] = bool(data)
        input_hash = sha256_file(input_path)
        text = data.decode(errors="replace")
    if export and input_hash:
        checks["hash_matches_export"] = input_hash == export.qir_sha256
    resource_match = _RESOURCE_COUNTS.search(text)
    if resource_match:
        required_qubits = int(resource_match.group("qubits"))
        required_results = int(resource_match.group("results"))
        checks["resource_counts_match"] = bool(
            export
            and required_qubits == export.source_qubits
            and required_results == export.measurement_count
        )
    pairs: list[tuple[int, int]] = []
    try:
        pairs = _measurement_pairs(text)
    except Exception as exc:
        diagnostics.append(f"Measurement resource parsing failed: {type(exc).__name__}: {exc}")
    measurement_count = len(pairs)
    result_count = len(
        re.findall(
            r"^\s*call void @__quantum__rt__result_record_output\(",
            text,
            flags=re.MULTILINE,
        )
    )
    gate_calls = len(
        re.findall(
            r"^\s*call void @__quantum__qis__(?!mz__body)[a-z0-9_]+__body\(",
            text,
            flags=re.MULTILINE,
        )
    )
    if export:
        checks["measurement_count_matches"] = measurement_count == export.measurement_count
        checks["result_output_count_matches"] = result_count == export.measurement_count
        checks["logical_measurement_pairs_complete"] = set(pairs) == {
            (index, index) for index in range(export.source_qubits)
        }
        transformed_quantum_ops = export.transformed_operations - export.measurement_count
        checks["operation_accounting_matches"] = (
            export.omitted_operation_count == 0
            and not export.unsupported_operations
            and gate_calls == transformed_quantum_ops
        )
        checks["source_metadata_agrees"] = bool(
            export.qir_path == _relative(root, input_path)
            and export.qir_size_bytes == input_path.stat().st_size
            and export.measurement_count == export.source_qubits
            and export.logical_to_qir_mapping_verified
        ) if input_path.is_file() else False
        bitcode_path = root / export.qir_bitcode_path
        checks["bitcode_matches_export"] = bool(
            bitcode_path.is_file() and sha256_file(bitcode_path) == export.qir_bitcode_sha256
        )
        mapping_path = input_path.parent / "qir_output_mapping.json"
        if mapping_path.is_file():
            try:
                mapping = QIROutputMapping.model_validate_json(mapping_path.read_text())
                checks["mapping_report_complete"] = bool(
                    mapping.logical_to_qir_mapping_verified
                    and not mapping.provider_result_order_verified
                    and len(mapping.entries) == export.source_qubits
                    and mapping.qir_sha256 == export.qir_sha256
                )
            except Exception as exc:
                diagnostics.append(f"Mapping report failed: {type(exc).__name__}: {exc}")
    try:
        import pyqir

        module = pyqir.Module.from_ir(pyqir.Context(), text)
        checks["llvm_module_parses"] = True
        module.verify()
        checks["llvm_module_verifies"] = True
    except Exception as exc:
        diagnostics.append(f"LLVM validation failed: {type(exc).__name__}: {exc}")
    declarations = re.findall(r"^declare\s+.+?@([^\s(]+)\(", text, flags=re.MULTILINE)
    checks["no_unresolved_non_qir_symbols"] = bool(declarations) and all(
        name.startswith("__quantum__") for name in declarations
    )
    checks["no_absolute_local_paths"] = not bool(_ABSOLUTE_PATH.search(text))
    checks["no_credential_like_material"] = not bool(_CREDENTIAL.search(text))
    try:
        checks["fixture_structural_validation_passed"] = _fixture_structural_validation()
    except Exception as exc:
        diagnostics.append(f"Fixture QIR validation failed: {type(exc).__name__}: {exc}")
    if export and export.source_qasm_path:
        source = root / export.source_qasm_path
        try:
            inspection, parsed = inspect_circuit(source)
            frozen_hash = read_sha256sums(source.parent / "SHA256SUMS").get(source.name)
            checks["source_hash_matches_frozen"] = bool(
                frozen_hash and frozen_hash == inspection.source_sha256 == export.source_qasm_sha256
            )
            if parsed.sdk_circuit is not None and checks["source_hash_matches_frozen"]:
                rebuilt = build_qir(parsed.sdk_circuit, module_name="p12_helios_qir")
                checks["reproducible_from_frozen_source"] = rebuilt.text == text
        except Exception as exc:
            diagnostics.append(f"Reproducibility check failed: {type(exc).__name__}: {exc}")
    else:
        # Mapping/fixture artifacts are deterministic but their source is an in-memory circuit.
        checks["reproducible_from_frozen_source"] = bool(export and export.source_qasm_path is None)
        checks["source_hash_matches_frozen"] = bool(export and export.source_qasm_path is None)
    for name, passed in checks.items():
        if not passed:
            diagnostics.append(f"Failed check: {name}")
    status: Literal["passed", "failed"] = "passed" if all(checks.values()) else "failed"
    validation = QIRValidationReport(
        status=status,
        input_path=_relative(root, input_path),
        input_sha256=input_hash,
        export_report_path=_relative(root, report_path) if report_path else None,
        evidence_levels=["structural", "resource_count"],
        validation_level="LLVM parse/verify + static QIR resource and operation accounting",
        checks=checks,
        required_num_qubits=required_qubits,
        required_num_results=required_results,
        measurement_call_count=measurement_count,
        result_output_count=result_count,
        qir_gate_call_count=gate_calls,
        logical_to_qir_mapping_verified=checks["logical_measurement_pairs_complete"]
        and checks["mapping_report_complete"],
        fixture_semantic_validation_level=(
            "structural_only_no_local_qir_execution_engine"
            if checks["fixture_structural_validation_passed"]
            else "failed"
        ),
        diagnostics=diagnostics,
        package_versions=package_versions(),
        input_hashes={_relative(root, input_path): input_hash} if input_hash else {},
    )
    if write_report:
        output_dir = root / "results/qir"
        write_json(output_dir / "qir_validation_report.json", validation)
        (output_dir / "qir_validation_report.md").write_text(
            "# QIR validation\n\n"
            f"Status: **{validation.status}**\n\n"
            f"Level: {validation.validation_level}\n\n"
            f"Resources: {required_qubits} qubits, {required_results} results  \n"
            f"Measurements: {measurement_count}\n\n"
            "This evidence does not establish P12 semantic equivalence or provider output order.\n"
        )
    return validation
