from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .circuit_inspection import inspect_circuit
from .hashing import read_sha256sums, sha256_file
from .mapping_validation import make_validation_circuit, validation_patterns
from .models import (
    MappingSyntaxCheckAggregateReport,
    QIRArtifactManifest,
    QIRExportReport,
    QIRMappingCaseExport,
    QIRMappingCasesReport,
    QIROutputMapping,
    QIROutputMappingEntry,
)
from .reporting import package_versions, write_json

CANONICAL_ORDER: Literal["logical_q0_to_q97_left_to_right"] = (
    "logical_q0_to_q97_left_to_right"
)
QIR_PROFILE = "BASE"
QIR_FORMAT = "LLVM_IR_TEXT"
CONVERSION_API = "pytket.qir.conversion.api.pytket_to_qir"
_MEASURE = re.compile(
    r"^\s*call void @__quantum__qis__mz__body\(ptr "
    r"(?P<qubit>null|inttoptr \(i64 \d+ to ptr\)), ptr "
    r"(?P<result>null|inttoptr \(i64 \d+ to ptr\))\)",
    flags=re.MULTILINE,
)
_REQUIRED = re.compile(
    r'"required_num_qubits"="(?P<qubits>\d+)".*"required_num_results"="(?P<results>\d+)"'
)


class QIRExportError(RuntimeError):
    """Raised when an exact and auditable QIR conversion cannot be produced."""


@dataclass(frozen=True)
class BuiltQIR:
    circuit: Any
    text: str
    bitcode: bytes
    operation_counts: dict[str, int]
    mapping: QIROutputMapping


def _pointer_index(value: str) -> int:
    value = value.strip()
    if value == "null":
        return 0
    match = re.fullmatch(r"inttoptr \(i64 (\d+) to ptr\)", value)
    if not match:
        raise QIRExportError(f"Unrecognized static QIR resource pointer: {value}")
    return int(match.group(1))


def _measurement_pairs(qir_text: str) -> list[tuple[int, int]]:
    return [
        (_pointer_index(match.group("qubit")), _pointer_index(match.group("result")))
        for match in _MEASURE.finditer(qir_text)
    ]


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise QIRExportError(f"Output must remain inside the repository: {path.name}") from exc


def _stable_circuit_hash(circuit: Any) -> str:
    payload = json.dumps(circuit.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _validate_numeric_parameters(circuit: Any) -> None:
    for command in circuit.get_commands():
        for parameter in command.op.params:
            try:
                finite = math.isfinite(float(parameter))
            except (TypeError, ValueError) as exc:
                raise QIRExportError(f"Non-numerical parameter in {command.op.type.name}") from exc
            if not finite:
                raise QIRExportError(f"Non-finite parameter in {command.op.type.name}")


def _append_explicit_measurements(circuit: Any) -> None:
    if circuit.n_bits or circuit.n_gates_of_type(_op_type("Measure")):
        raise QIRExportError("Input circuit must not contain classical bits or measurements")
    for logical in range(circuit.n_qubits):
        register = circuit.add_c_register(f"m{logical:03d}", 1)
        circuit.Measure(logical, register[0])
    if [str(bit) for bit in circuit.bits] != [f"m{index:03d}[0]" for index in range(circuit.n_qubits)]:
        raise QIRExportError("Explicit result register order is not deterministic")


def _op_type(name: str) -> Any:
    from pytket.circuit import OpType

    return getattr(OpType, name)


def _rebase_for_qir(circuit: Any) -> None:
    from pytket.circuit import OpType
    from pytket.passes import AutoRebase

    gate_set = {OpType.Rz, OpType.Rx, OpType.Ry, OpType.CZ, OpType.X}
    AutoRebase(gate_set).apply(circuit)
    if circuit.has_implicit_wireswaps:
        raise QIRExportError("QIR preparation created unresolved implicit wire swaps")
    permutation = circuit.implicit_qubit_permutation()
    if any(source != target for source, target in permutation.items()):
        raise QIRExportError("QIR preparation created a non-identity qubit permutation")


def _verify_qir_operation_accounting(circuit: Any, qir_text: str) -> dict[str, int]:
    expected = Counter(command.op.type.name for command in circuit.get_commands())
    names = Counter(
        match.group(1)
        for match in re.finditer(
            r"^\s*call void @__quantum__qis__([a-z0-9_]+)__body\(",
            qir_text,
            flags=re.MULTILINE,
        )
    )
    mapping = {"Rz": "rz", "Rx": "rx", "Ry": "ry", "CZ": "cz", "X": "x", "Measure": "mz"}
    unsupported = sorted(set(expected) - set(mapping))
    if unsupported:
        raise QIRExportError(f"Unsupported transformed operations: {unsupported}")
    mismatches = {
        operation: (count, names.get(mapping[operation], 0))
        for operation, count in expected.items()
        if names.get(mapping[operation], 0) != count
    }
    if mismatches:
        raise QIRExportError(f"QIR operation accounting mismatch: {mismatches}")
    return dict(sorted(expected.items()))


def build_qir(circuit: Any, *, module_name: str) -> BuiltQIR:
    """Build deterministic textual QIR and verified LLVM bitcode without writing files."""
    if circuit.n_qubits != 98:
        raise QIRExportError("Milestone 3 QIR artifacts require exactly 98 qubits")
    _validate_numeric_parameters(circuit)
    prepared = circuit.copy()
    _rebase_for_qir(prepared)
    _append_explicit_measurements(prepared)

    from pytket.qir.conversion.api import (
        QIRFormat,
        QIRProfile,
        check_circuit,
        pytket_to_qir,
    )

    check_circuit(prepared)
    rendered = pytket_to_qir(
        prepared,
        name=module_name,
        qir_format=QIRFormat.STRING,
        profile=QIRProfile.BASE,
    )
    if not isinstance(rendered, str) or not rendered.strip():
        raise QIRExportError("pytket-qir did not return nonempty textual QIR")
    # Strip unused declarations that strict syntax validators reject (e.g. read_result in Base Profile)
    rendered = rendered.replace("declare i1 @__quantum__qis__read_result__body(ptr)\n", "")
    rendered = rendered.replace("declare i1 @__quantum__qis__read_result__body(ptr)", "")
    required = _REQUIRED.search(rendered)
    if not required or (int(required.group("qubits")), int(required.group("results"))) != (98, 98):
        raise QIRExportError("QIR module does not declare exactly 98 qubits and 98 results")
    measurement_pairs = _measurement_pairs(rendered)
    if len(measurement_pairs) != 98 or set(measurement_pairs) != {(i, i) for i in range(98)}:
        raise QIRExportError("QIR measurements do not preserve the logical-to-result identity map")
    operation_counts = _verify_qir_operation_accounting(prepared, rendered)

    import pyqir

    module = pyqir.Module.from_ir(pyqir.Context(), rendered)
    module.verify()
    bitcode = bytes(module.bitcode)
    if not bitcode:
        raise QIRExportError("LLVM produced empty QIR bitcode")
    mapping = QIROutputMapping(
        number_of_qubits=98,
        entries=[
            QIROutputMappingEntry(
                logical_qubit_index=index,
                logical_qubit_name=f"q[{index}]",
                pytket_qubit_index=index,
                qir_qubit_index=index,
                qir_result_index=index,
                canonical_position=index,
            )
            for index in range(98)
        ],
        logical_to_qir_mapping_verified=True,
        qir_profile=QIR_PROFILE,
        package_versions=package_versions(),
    )
    return BuiltQIR(prepared, rendered, bitcode, operation_counts, mapping)


def _persist_qir_export(
    root: Path,
    *,
    built: BuiltQIR,
    output: Path,
    report_path: Path,
    mapping_path: Path,
    source_path: Path | None,
    source_hash: str,
    source_operations: int,
    source_two_qubit_gates: int,
    source_measurements: int,
) -> QIRExportReport:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(built.text)
    bitcode_path = output.with_suffix(".bc")
    bitcode_path.write_bytes(built.bitcode)
    qir_hash = sha256_file(output)
    bitcode_hash = sha256_file(bitcode_path)
    mapping = built.mapping.model_copy(
        update={
            "qir_sha256": qir_hash,
            "input_hashes": {_relative(root, output): qir_hash},
        }
    )
    write_json(mapping_path, mapping)
    report = QIRExportReport(
        status="success",
        source_qasm_path=_relative(root, source_path) if source_path else None,
        source_qasm_sha256=source_hash,
        source_qubits=98,
        source_operations=source_operations,
        source_two_qubit_gates=source_two_qubit_gates,
        source_measurements=source_measurements,
        transformed_operation_counts=built.operation_counts,
        transformed_operations=sum(built.operation_counts.values()),
        measurement_count=built.operation_counts.get("Measure", 0),
        canonical_order=CANONICAL_ORDER,
        qir_format=QIR_FORMAT,
        qir_profile=QIR_PROFILE,
        qir_path=_relative(root, output),
        qir_sha256=qir_hash,
        qir_size_bytes=output.stat().st_size,
        qir_bitcode_path=_relative(root, bitcode_path),
        qir_bitcode_sha256=bitcode_hash,
        qir_bitcode_size_bytes=bitcode_path.stat().st_size,
        conversion_api=CONVERSION_API,
        conversion_preflight_passed=True,
        unsupported_operations=[],
        omitted_operation_count=0,
        logical_to_qir_mapping_verified=True,
        package_versions=package_versions(),
        input_hashes={
            (_relative(root, source_path) if source_path else "deterministic_circuit"): source_hash
        },
    )
    write_json(report_path, report)
    return report


def export_p12_qir(root: Path, source: Path, output: Path) -> QIRExportReport:
    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise QIRExportError(f"Source QASM does not exist: {source.name}")
    frozen = read_sha256sums(source.parent / "SHA256SUMS").get(source.name)
    source_hash = sha256_file(source)
    if not frozen or frozen != source_hash:
        raise QIRExportError("Source QASM hash does not match its frozen SHA256SUMS entry")
    inspection, parsed = inspect_circuit(source)
    if parsed.sdk_circuit is None:
        raise QIRExportError("pytket did not produce a source circuit")
    if inspection.number_of_qubits != 98:
        raise QIRExportError("P12 source does not have exactly 98 qubits")
    if inspection.source_contains_measurements or inspection.number_of_classical_bits:
        raise QIRExportError("Frozen P12 source unexpectedly contains classical output state")
    if inspection.has_symbolic_parameters or not inspection.all_numerical_angles_finite:
        raise QIRExportError("P12 source parameters are not fully numerical and finite")
    built = build_qir(parsed.sdk_circuit, module_name="p12_helios_qir")
    output_dir = output.parent
    report = _persist_qir_export(
        root,
        built=built,
        output=output,
        report_path=output_dir / "qir_export_report.json",
        mapping_path=output_dir / "qir_output_mapping.json",
        source_path=source,
        source_hash=source_hash,
        source_operations=inspection.gates.total_operations,
        source_two_qubit_gates=inspection.gates.two_qubit_gates,
        source_measurements=inspection.gates.measurements,
    )
    manifest = QIRArtifactManifest(
        artifact_paths={
            "llvm_ir": report.qir_path,
            "bitcode": report.qir_bitcode_path,
            "export_report": _relative(root, output_dir / "qir_export_report.json"),
            "output_mapping": _relative(root, output_dir / "qir_output_mapping.json"),
        },
        artifact_hashes={
            "llvm_ir": report.qir_sha256,
            "bitcode": report.qir_bitcode_sha256,
        },
        source_hash=source_hash,
        conversion_configuration={
            "profile": QIR_PROFILE,
            "format": QIR_FORMAT,
            "rebase_gate_set": ["CZ", "Rx", "Ry", "Rz", "X"],
            "result_registers": "98 distinct one-bit registers m000 through m097",
        },
        package_versions=package_versions(),
        input_hashes={_relative(root, source): source_hash},
    )
    write_json(output_dir / "qir_manifest.json", manifest)
    (output_dir / "qir_export_report.md").write_text(
        "# P12 QIR export\n\n"
        f"Status: **{report.status}**\n\n"
        f"Profile: `{report.qir_profile}`  \n"
        f"Measurements: **{report.measurement_count}**  \n"
        f"LLVM IR SHA-256: `{report.qir_sha256}`  \n"
        f"Bitcode SHA-256: `{report.qir_bitcode_sha256}`\n\n"
        "Logical q[i] maps to QIR qubit i and result i. Provider result position remains unresolved.\n"
    )
    return report


def export_mapping_qir_cases(root: Path) -> QIRMappingCasesReport:
    base = root / "results/qir/mapping_cases"
    cases: list[QIRMappingCaseExport] = []
    for case_name, pattern in validation_patterns().items():
        circuit = make_validation_circuit(pattern, measurements=False)
        built = build_qir(circuit, module_name=f"p12_mapping_{case_name}")
        case_dir = base / case_name
        source_hash = _stable_circuit_hash(circuit)
        report = _persist_qir_export(
            root,
            built=built,
            output=case_dir / "circuit.ll",
            report_path=case_dir / "export_report.json",
            mapping_path=case_dir / "qir_output_mapping.json",
            source_path=None,
            source_hash=source_hash,
            source_operations=len(circuit.get_commands()),
            source_two_qubit_gates=0,
            source_measurements=0,
        )
        write_json(
            case_dir / "expected_output.json",
            {
                "case_name": case_name,
                "canonical_order": CANONICAL_ORDER,
                "expected_canonical_string": pattern,
                "provider_result_position": None,
            },
        )
        cases.append(
            QIRMappingCaseExport(
                case_name=case_name,
                expected_canonical_string=pattern,
                qir_path=report.qir_path,
                qir_sha256=report.qir_sha256,
                export_report_path=_relative(root, case_dir / "export_report.json"),
                mapping_path=_relative(root, case_dir / "qir_output_mapping.json"),
                status="passed",
            )
        )
    aggregate = QIRMappingCasesReport(
        status="passed",
        cases=cases,
        total_cases=len(cases),
        passed_cases=sum(case.status == "passed" for case in cases),
        reversal_sensitive=all(
            pattern != pattern[::-1]
            for name, pattern in validation_patterns().items()
            if name not in {"all_zeros"}
        ),
        logical_to_qir_mapping_verified=True,
        package_versions=package_versions(),
        input_hashes={case.qir_path: case.qir_sha256 for case in cases},
    )
    write_json(base / "mapping_qir_export_report.json", aggregate)
    syntax_report_path = root / "results/nexus/syntax_check/mapping_cases_report.json"
    if not syntax_report_path.is_file():
        write_json(
            syntax_report_path,
            MappingSyntaxCheckAggregateReport(
                status="not_submitted",
                target="Helios-1SC",
                ordered_cases=[case.case_name for case in cases],
                case_statuses={case.case_name: "local_qir_export_passed" for case in cases},
                p12_submission_allowed=False,
                local_logical_to_qir_mapping="passed",
                all_mapping_qir_syntax_checks="not_submitted",
                p12_qir_syntax_check="not_submitted",
                package_versions=package_versions(),
                input_hashes={case.qir_path: case.qir_sha256 for case in cases},
            ),
        )
    return aggregate
