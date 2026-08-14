from __future__ import annotations

from pathlib import Path
from typing import Any

from .backends.quantinuum import QuantinuumCompilationBackend, sanitize_diagnostic
from .bit_ordering import raw_value_to_canonical
from .config import load_model
from .hashing import sha256_file
from .models import (
    CompilationConfig,
    MappingValidationCase,
    MappingValidationReport,
    MeasurementMapping,
)
from .reporting import package_versions, write_json


def validation_patterns(number_of_qubits: int = 98) -> dict[str, str]:
    if number_of_qubits != 98:
        raise ValueError("P12 mapping validation requires exactly 98 qubits")
    patterns = {
        "all_zeros": "0" * 98,
        "q0": "1" + "0" * 97,
        "q97": "0" * 97 + "1",
        "q0_q7_q31_q64_q97": "".join(
            "1" if index in {0, 7, 31, 64, 97} else "0" for index in range(98)
        ),
        "non_palindromic_blocks": "1" * 3 + "0" * 11 + "1" * 17 + "0" * 29 + "1" * 7 + "0" * 31,
        "alternating_q0_one": "".join("1" if index % 2 == 0 else "0" for index in range(98)),
    }
    if any(len(value) != 98 for value in patterns.values()):
        raise AssertionError("Internal mapping-validation pattern has wrong width")
    if patterns["non_palindromic_blocks"] == patterns["non_palindromic_blocks"][::-1]:
        raise AssertionError("Block pattern must not be palindromic")
    if patterns["alternating_q0_one"] == patterns["alternating_q0_one"][::-1]:
        raise AssertionError("Alternating pattern must expose reversal")
    return patterns


def make_validation_circuit(pattern: str, *, measurements: bool = True) -> Any:
    if len(pattern) != 98 or set(pattern) - {"0", "1"}:
        raise ValueError("Prepared mapping pattern must contain exactly 98 bits")
    from pytket import Circuit

    circuit = Circuit(98, 98 if measurements else 0, name="mapping_validation")
    for index, bit in enumerate(pattern):
        if bit == "1":
            circuit.X(index)
    if measurements:
        for index in range(98):
            circuit.Measure(index, index)
    return circuit


def validate_observed_case(
    case_name: str, prepared: str, raw_provider_output: Any, mapping: MeasurementMapping
) -> MappingValidationCase:
    canonical = raw_value_to_canonical(raw_provider_output, mapping)
    return MappingValidationCase(
        case_name=case_name,
        prepared_logical_string=prepared,
        raw_provider_output="".join(str(value) for value in raw_provider_output)
        if not isinstance(raw_provider_output, str)
        else raw_provider_output,
        canonical_output=canonical,
        mapping_correct=canonical == prepared,
        status="passed" if canonical == prepared else "failed",
    )


def run_mapping_validation(
    root: Path,
    *,
    target: str | None,
    mode: str,
    config_path: Path | None = None,
) -> MappingValidationReport:
    output = root / "results/mapping_validation"
    cases_dir = output / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    config = load_model(config_path or root / "configs/compilation.yaml", CompilationConfig)
    cases: list[MappingValidationCase] = []
    diagnostics: list[str] = []
    for name, pattern in validation_patterns().items():
        circuit = make_validation_circuit(pattern)
        derived_path = cases_dir / f"{name}.qasm"
        from pytket.qasm import circuit_to_qasm  # type: ignore[attr-defined]

        circuit_to_qasm(circuit, str(derived_path), maxwidth=98)
        prepared_hash = sha256_file(derived_path)
        compiled_hash: str | None = None
        status = "prepared"
        if target:
            try:
                artifact = QuantinuumCompilationBackend(target).compile(circuit, config)
                compiled_path = cases_dir / f"{name}.compiled.qasm"
                circuit_to_qasm(artifact.circuit, str(compiled_path), maxwidth=98)
                compiled_hash = sha256_file(compiled_path)
                status = "compiled_not_executed"
            except Exception as exc:
                diagnostics.append(f"{name}: {sanitize_diagnostic(exc)}")
                status = "compile_failed"
        case = MappingValidationCase(
            case_name=name,
            prepared_logical_string=pattern,
            prepared_circuit_hash=prepared_hash,
            compiled_circuit_hash=compiled_hash,
            status=status,
        )
        cases.append(case)
        write_json(cases_dir / f"{name}.json", case.model_dump(mode="json"))
    report = MappingValidationReport(
        status="incomplete",
        target=target,
        mode=mode,
        cases=cases,
        passed_cases=0,
        total_cases=len(cases),
        diagnostics=[
            *diagnostics,
            "Milestone 2 has no process_circuit path; import emulator results to validate provider ordering",
        ],
        package_versions=package_versions(),
    )
    write_json(output / "mapping_validation_report.json", report)
    table = "\n".join(f"| {case.case_name} | {case.status} |" for case in cases)
    (output / "mapping_validation_report.md").write_text(
        "# Mapping validation\n\nStatus: **incomplete** (no circuit was submitted).\n\n"
        "| Case | Status |\n|---|---|\n"
        + table
        + "\n\nProvider/emulator results must be imported before readiness can pass.\n"
    )
    return report
