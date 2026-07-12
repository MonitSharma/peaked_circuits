from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .backends.quantinuum import QuantinuumCompilationBackend
from .bit_ordering import build_measurement_mapping
from .circuit_inspection import inspect_circuit
from .config import config_digest, load_model
from .hashing import sha256_file
from .models import CompilationConfig, CompilationReport, MeasurementMapping, ValidationResult
from .reporting import package_versions, write_json


def _circuit_summary(circuit: Any) -> dict[str, Any]:
    counts: dict[str, int] = {}
    one = two = measurements = resets = conditionals = 0
    for command in circuit.get_commands():
        name = command.op.type.name
        counts[name] = counts.get(name, 0) + 1
        qubits = len(command.qubits)
        one += qubits == 1 and name not in {"Measure", "Reset"}
        two += qubits == 2
        measurements += name == "Measure"
        resets += name == "Reset"
        conditionals += name == "Conditional"
    return {
        "qubit_count": circuit.n_qubits,
        "classical_bit_count": circuit.n_bits,
        "gate_counts": dict(sorted(counts.items())),
        "gate_set": sorted(counts),
        "total_gate_count": len(circuit.get_commands()),
        "one_qubit_gate_count": one,
        "two_qubit_gate_count": two,
        "total_depth": circuit.depth(),
        "two_qubit_depth": circuit.depth_2q(),
        "measurements": measurements,
        "reset_operations": resets,
        "conditional_operations": conditionals,
    }


def _ratio(new: int, old: int) -> dict[str, Any]:
    return {
        "difference": new - old,
        "ratio": new / old if old else None,
        "ratio_explanation": None if old else "Original denominator is zero",
    }


def _trace_measurements(circuit: Any, number_of_logical_qubits: int) -> MeasurementMapping:
    expected_units = {("q", i) for i in range(number_of_logical_qubits)}
    actual_units = {
        (qubit.reg_name, int(qubit.index[0])) for qubit in circuit.qubits if len(qubit.index) == 1
    }
    if actual_units != expected_units:
        raise RuntimeError(
            "Compiled qubit units do not preserve traceable q[i] identities; refusing to guess routing"
        )
    logical_to_classical: dict[int, int] = {}
    for command in circuit.get_commands():
        if command.op.type.name != "Measure":
            continue
        qubit, bit = command.qubits[0], command.bits[0]
        if qubit.reg_name != "q" or len(qubit.index) != 1 or len(bit.index) != 1:
            raise RuntimeError("Measurement units are not unambiguously indexable")
        logical_to_classical[int(qubit.index[0])] = int(bit.index[0])
    if set(logical_to_classical) != set(range(number_of_logical_qubits)):
        raise RuntimeError("Compiled measurement mapping is incomplete")
    bit_indices = sorted({int(bit.index[0]) for bit in circuit.bits if len(bit.index) == 1})
    if bit_indices != list(range(len(bit_indices))):
        raise RuntimeError(
            "Compiled classical-bit layout is not contiguous and needs an explicit SDK map"
        )
    return build_measurement_mapping(
        logical_to_classical=logical_to_classical,
        logical_to_physical={i: i for i in range(number_of_logical_qubits)},
        sdk_string_order="msb_left",
        register_layout=[{"name": "c", "classical_indices": bit_indices}],
    )


def compile_from_config(root: Path, config_path: Path) -> CompilationReport:
    config = load_model(config_path, CompilationConfig)
    source = root / config.source_circuit
    inspection, parsed = inspect_circuit(source)
    device_name = config.backend.get("device_name") or os.environ.get("P12_QUANTINUUM_DEVICE")
    adapter = QuantinuumCompilationBackend(device_name)
    descriptor = adapter.describe()
    start = datetime.now(UTC)
    timer = time.perf_counter()
    original = {
        "qubit_count": inspection.number_of_qubits,
        "gate_counts": inspection.gates.counts_by_gate,
        "gate_set": sorted(inspection.gates.counts_by_gate),
        "total_gate_count": inspection.gates.total_operations,
        "one_qubit_gate_count": inspection.gates.one_qubit_gates,
        "two_qubit_gate_count": inspection.gates.two_qubit_gates,
        "total_depth": inspection.gates.circuit_depth,
        "two_qubit_depth": inspection.gates.two_qubit_depth,
        "measurement_status": inspection.source_contains_measurements,
        "source_hash": inspection.source_sha256,
    }
    output_dir = root / str(config.output.get("directory", "results/compilation"))
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        if parsed.sdk_circuit is None:
            raise RuntimeError("pytket parser circuit is unavailable")
        if not device_name:
            raise RuntimeError("No target device configured; compilation is environment-limited")
        derived = parsed.sdk_circuit.copy()
        if (
            config.measurement.get("append_measure_all", True)
            and not inspection.source_contains_measurements
        ):
            derived.measure_all()
        compiled = adapter.compile(derived, config)
        mapping = _trace_measurements(compiled, inspection.number_of_qubits)
        backend_validation = adapter.validate(compiled)
        structural_predicates = {
            "exactly_98_logical_qubits": compiled.n_qubits == 98,
            "classical_bit_for_every_logical_qubit": compiled.n_bits >= 98,
            "complete_unique_measurement_mapping": len(mapping.entries) == 98,
            "output_circuit_nonempty": bool(compiled.n_gates),
            "all_numerical_parameters_finite": inspection.all_numerical_angles_finite,
            "all_logical_qubits_traceable": True,
        }
        validation = ValidationResult(
            passed=all(structural_predicates.values()) and backend_validation.passed,
            predicates={**structural_predicates, **backend_validation.predicates},
            diagnostics=backend_validation.diagnostics,
        )
        summary = _circuit_summary(compiled)
        summary["unsupported_instructions"] = (
            [] if validation.passed else ["See validation predicates"]
        )
        summary["all_logical_qubits_represented"] = compiled.n_qubits == inspection.number_of_qubits
        from pytket.qasm import circuit_to_qasm  # type: ignore[attr-defined]

        compiled_path = root / "circuits/compiled/peaked_circuit_P12_Hqap_98x2457.compiled.qasm"
        circuit_to_qasm(compiled, str(compiled_path))
        summary["compiled_qasm_hash"] = sha256_file(compiled_path)
        write_json(output_dir / "measurement_mapping.json", mapping)
        overhead = {
            key: _ratio(int(summary[new_key]), cast(int, original[old_key]))
            for key, new_key, old_key in [
                ("total_gate_count", "total_gate_count", "total_gate_count"),
                ("one_qubit_gate_count", "one_qubit_gate_count", "one_qubit_gate_count"),
                ("two_qubit_gate_count", "two_qubit_gate_count", "two_qubit_gate_count"),
                ("total_depth", "total_depth", "total_depth"),
                ("two_qubit_depth", "two_qubit_depth", "two_qubit_depth"),
            ]
        }
        report = CompilationReport(
            status="success",
            backend=descriptor,
            original=original,
            compiled=summary,
            overhead=overhead,
            validation=validation,
            start_timestamp=start,
            end_timestamp=datetime.now(UTC),
            wall_clock_seconds=time.perf_counter() - timer,
            configuration=config.model_dump(mode="json"),
            configuration_hash=config_digest(config_path),
            package_versions=package_versions(),
            input_hashes={str(source): sha256_file(source)},
            random_seed=config.compiler.get("seed"),
        )
    except Exception as exc:
        blocked = isinstance(exc, RuntimeError) and (
            not device_name or not descriptor.available or not descriptor.credentials_detected
        )
        report = CompilationReport(
            status="blocked" if blocked else "failed",
            backend=descriptor,
            original=original,
            start_timestamp=start,
            end_timestamp=datetime.now(UTC),
            wall_clock_seconds=time.perf_counter() - timer,
            failure={
                "exception_type": type(exc).__name__,
                "sanitized_message": str(exc),
                "stage": "target_configuration" if not device_name else "compilation",
                "suggested_next_step": "Configure a currently available Quantinuum target, then rerun compile-only validation.",
            },
            configuration=config.model_dump(mode="json"),
            configuration_hash=config_digest(config_path),
            package_versions=package_versions(),
            input_hashes={str(source): sha256_file(source)},
            random_seed=config.compiler.get("seed"),
        )
    write_json(output_dir / "compilation_report.json", report)
    write_json(output_dir / "configuration_snapshot.json", config.model_dump(mode="json"))
    write_json(
        output_dir / "validation_result.json",
        report.validation
        or ValidationResult(
            passed=False,
            predicates={"compilation_completed": False},
            diagnostics=[
                report.failure["sanitized_message"] if report.failure else "Compilation incomplete"
            ],
        ),
    )
    (output_dir / "compiler_diagnostics.log").write_text(
        json.dumps(report.failure or {"status": "success"}, indent=2) + "\n"
    )
    (output_dir / "compilation_report.md").write_text(
        f"# Compilation report\n\nStatus: **{report.status}**\n\nTarget: `{device_name}`\n\n"
        + (
            f"Blocker: {report.failure['sanitized_message']}\n"
            if report.failure
            else f"Backend validation passed: {report.validation.passed if report.validation else False}\n"
        )
        + "\nNo hardware submission was attempted and no paid resources were consumed.\n"
    )
    return report


def validate_existing(root: Path) -> ValidationResult:
    report_path = root / "results/compilation/compilation_report.json"
    if not report_path.is_file():
        return ValidationResult(
            passed=False,
            predicates={"compilation_report_exists": False},
            diagnostics=["Run p12-recovery compile first"],
        )
    report = CompilationReport.model_validate_json(report_path.read_text())
    predicates = {
        "compilation_succeeded": report.status == "success",
        "exactly_98_logical_qubits": (report.compiled or {}).get("qubit_count") == 98,
        "backend_validation_passed": report.validation.passed if report.validation else False,
        "source_hash_recorded": bool(report.original.get("source_hash")),
        "hardware_not_attempted": True,
        "paid_resources_not_consumed": True,
    }
    result = ValidationResult(
        passed=all(predicates.values()),
        predicates=predicates,
        diagnostics=[]
        if all(predicates.values())
        else ["Compilation or backend validation remains incomplete"],
    )
    write_json(root / "results/compilation/validation_result.json", result)
    return result
