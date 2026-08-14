from __future__ import annotations

import json
import math
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .backends.quantinuum import (
    CompiledCircuitArtifact,
    QuantinuumCompilationBackend,
    discover_quantinuum_report,
    sanitize_diagnostic,
)
from .bit_ordering import build_measurement_mapping
from .circuit_inspection import inspect_circuit
from .config import config_digest, load_model
from .hashing import read_sha256sums, sha256_file
from .models import (
    AvailableDevicesReport,
    BackendDescriptor,
    CompilationConfig,
    CompilationReport,
    MeasurementMapping,
    ValidationResult,
)
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


def build_register_layout(circuit: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Use actual circuit bit order; never lexical register sorting."""
    bit_to_global = {str(bit): position for position, bit in enumerate(circuit.bits)}
    registers: dict[str, list[tuple[int, int]]] = {}
    register_order: list[str] = []
    for bit in circuit.bits:
        if len(bit.index) != 1:
            raise RuntimeError(f"Classical bit is not one-dimensionally indexable: {bit}")
        name = str(bit.reg_name)
        if name not in registers:
            registers[name] = []
            register_order.append(name)
        registers[name].append((int(bit.index[0]), bit_to_global[str(bit)]))
    layout = []
    for provider_order, name in enumerate(register_order):
        values = registers[name]
        layout.append(
            {
                "name": name,
                "provider_order": provider_order,
                "provider_bit_order": "msb_left",
                "bit_indices": [local for local, _ in values],
                "classical_indices": [global_index for _, global_index in values],
                "ordering_source": "compiled_circuit.bits insertion order; requires mapping validation",
            }
        )
    return layout, bit_to_global


_UNIT = re.compile(r"^([^\[]+)\[(\d+)]$")


def _unit_index(name: str) -> int | None:
    match = _UNIT.fullmatch(name)
    return int(match.group(2)) if match else None


def trace_measurements(
    artifact: CompiledCircuitArtifact, number_of_logical_qubits: int
) -> MeasurementMapping:
    circuit = artifact.circuit
    expected = {f"q[{index}]" for index in range(number_of_logical_qubits)}
    if set(artifact.final_map) != expected:
        missing = sorted(expected - set(artifact.final_map))
        extra = sorted(set(artifact.final_map) - expected)
        raise RuntimeError(
            f"Compilation permutation is incomplete; missing={missing}, extra={extra}"
        )
    compiled_names = {
        index: artifact.final_map[f"q[{index}]"] for index in range(number_of_logical_qubits)
    }
    if len(set(compiled_names.values())) != number_of_logical_qubits:
        raise RuntimeError("Compilation final_map contains duplicate output qubits")
    layout, bit_to_global = build_register_layout(circuit)
    measured: dict[str, str] = {}
    for command in circuit.get_commands():
        if command.op.type.name != "Measure":
            continue
        compiled_name, bit_name = str(command.qubits[0]), str(command.bits[0])
        if compiled_name in measured:
            raise RuntimeError(f"Compiled qubit is measured more than once: {compiled_name}")
        measured[compiled_name] = bit_name
    logical_to_classical: dict[int, int] = {}
    for logical, compiled_name in compiled_names.items():
        measured_bit_name = measured.get(compiled_name)
        if measured_bit_name is None:
            raise RuntimeError(f"Logical q[{logical}] has no traceable measurement")
        logical_to_classical[logical] = bit_to_global[measured_bit_name]
    if len(set(logical_to_classical.values())) != number_of_logical_qubits:
        raise RuntimeError("A classical destination is reused by multiple logical qubits")
    compiled_indices = {logical: _unit_index(name) for logical, name in compiled_names.items()}
    physical = {
        logical: index
        for logical, name in compiled_names.items()
        if (index := _unit_index(name)) is not None and not name.startswith("q[")
    }
    mapping = build_measurement_mapping(
        logical_to_classical=logical_to_classical,
        logical_to_physical=physical if len(physical) == number_of_logical_qubits else None,
        logical_to_compiled_name=compiled_names,
        logical_to_compiled_index=compiled_indices,
        sdk_string_order="lsb_left",
        register_layout=layout,
        mapping_source="CompilationUnit.final_map + compiled Measure commands + circuit.bits order",
        mapping_confidence="high",
    )
    return mapping.model_copy(update={"unknown_permutation_count": 0, "complete": True})


def _select_live_descriptor(
    root: Path, device_name: str
) -> tuple[BackendDescriptor | None, list[str]]:
    path = root / "results/backend/available_devices.json"
    report: AvailableDevicesReport
    if path.is_file():
        try:
            report = AvailableDevicesReport.model_validate_json(path.read_text())
        except Exception:
            report = discover_quantinuum_report()
    else:
        report = discover_quantinuum_report()
    matches = [device for device in report.devices if device.device_name == device_name]
    nexus_matches = [device for device in matches if device.provider_api == "nexus"]
    if len(nexus_matches) == 1:
        return nexus_matches[0], report.diagnostics
    if len(matches) == 1:
        return matches[0], report.diagnostics
    return None, [
        *report.diagnostics,
        f"Exact device name not present in live discovery: {device_name}",
    ]


def compile_from_config(
    root: Path, config_path: Path, *, device_name_override: str | None = None
) -> CompilationReport:
    config = load_model(config_path, CompilationConfig)
    source = root / config.source_circuit
    inspection, parsed = inspect_circuit(source)
    device_name = (
        device_name_override
        or config.backend.get("device_name")
        or os.environ.get("P12_QUANTINUUM_DEVICE")
    )
    descriptor: BackendDescriptor | None = None
    discovery_diagnostics: list[str] = []
    if device_name:
        descriptor, discovery_diagnostics = _select_live_descriptor(root, str(device_name))
    adapter = QuantinuumCompilationBackend(
        str(device_name) if device_name else None, descriptor=descriptor
    )
    backend_descriptor = adapter.describe()
    start = datetime.now(UTC)
    timer = time.perf_counter()
    checksum_path = source.parent / "SHA256SUMS"
    frozen_hash = (
        read_sha256sums(checksum_path).get(source.name) if checksum_path.is_file() else None
    )
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
        "frozen_source_hash": frozen_hash,
    }
    output_dir = root / str(config.output.get("directory", "results/compilation"))
    output_dir.mkdir(parents=True, exist_ok=True)
    effective = {
        "device_name": device_name,
        "provider_api": descriptor.provider_api if descriptor else "unresolved",
        "device_name_source": "cli"
        if device_name_override
        else "config"
        if config.backend.get("device_name")
        else "environment"
        if os.environ.get("P12_QUANTINUUM_DEVICE")
        else None,
        **config.compiler,
    }
    try:
        if parsed.sdk_circuit is None:
            raise RuntimeError("pytket parser circuit is unavailable")
        if inspection.source_sha256 != frozen_hash:
            raise RuntimeError("P12 source hash does not match the frozen SHA256SUMS value")
        if inspection.number_of_qubits != 98:
            raise RuntimeError("P12 source width is not exactly 98")
        if not device_name:
            raise RuntimeError("No exact discovered target configured")
        if config.backend.get("require_live_metadata", True) and descriptor is None:
            raise RuntimeError(
                "Live target metadata is required: " + "; ".join(discovery_diagnostics)
            )
        if descriptor and not descriptor.has_at_least_98_qubits:
            raise RuntimeError("Selected target has fewer than 98 qubits")
        derived = parsed.sdk_circuit.copy()
        if (
            config.measurement.get("append_measure_all", True)
            and not inspection.source_contains_measurements
        ):
            derived.measure_all()
        artifact = adapter.compile(derived, config)
        effective.update(artifact.effective_options)
        mapping = trace_measurements(artifact, inspection.number_of_qubits)
        compiled = artifact.circuit
        backend_validation = adapter.validate(compiled)
        parameters_finite = all(
            math.isfinite(float(parameter))
            for command in compiled.get_commands()
            for parameter in command.op.params
        )
        structural = {
            "source_hash_matches_frozen": inspection.source_sha256 == frozen_hash,
            "original_width_exactly_98": inspection.number_of_qubits == 98,
            "compiled_width_within_target": descriptor is not None
            and compiled.n_qubits <= cast(int, descriptor.qubit_capacity),
            "exactly_98_logical_outputs": len(mapping.entries) == 98,
            "unique_logical_outputs": len({entry.logical_qubit_index for entry in mapping.entries})
            == 98,
            "unique_classical_destinations": len(
                {entry.classical_bit_index for entry in mapping.entries}
            )
            == 98,
            "all_parameters_finite": parameters_finite,
            "compiled_circuit_nonempty": bool(compiled.n_gates),
            "mapping_complete": mapping.complete,
            "unknown_permutation_count_zero": mapping.unknown_permutation_count == 0,
        }
        validation = ValidationResult(
            passed=all(structural.values()) and backend_validation.passed,
            predicates={**structural, **backend_validation.predicates},
            diagnostics=backend_validation.diagnostics,
        )
        summary = _circuit_summary(compiled)
        summary.update(
            {
                "unsupported_instructions": [] if backend_validation.passed else ["See predicates"],
                "compiled_initial_map": artifact.initial_map,
                "compiled_final_map": artifact.final_map,
                "logical_outputs": 98,
                "extra_classical_bits": compiled.n_bits - 98,
            }
        )
        from pytket.qasm import circuit_to_qasm  # type: ignore[attr-defined]

        compiled_path = root / "circuits/compiled/peaked_circuit_P12_Hqap_98x2457.compiled.qasm"
        circuit_to_qasm(compiled, str(compiled_path))
        summary["compiled_qasm_hash"] = sha256_file(compiled_path)
        write_json(output_dir / "measurement_mapping.json", mapping)
        write_json(
            output_dir / "register_layout.json", {"register_layout": mapping.register_layout}
        )
        overhead = {
            key: _ratio(int(summary[new]), cast(int, original[old]))
            for key, new, old in [
                ("total_gate_count", "total_gate_count", "total_gate_count"),
                ("one_qubit_gate_count", "one_qubit_gate_count", "one_qubit_gate_count"),
                ("two_qubit_gate_count", "two_qubit_gate_count", "two_qubit_gate_count"),
                ("total_depth", "total_depth", "total_depth"),
                ("two_qubit_depth", "two_qubit_depth", "two_qubit_depth"),
            ]
        }
        report = CompilationReport(
            status="success",
            backend=backend_descriptor,
            original=original,
            compiled=summary,
            overhead=overhead,
            validation=validation,
            start_timestamp=start,
            end_timestamp=datetime.now(UTC),
            wall_clock_seconds=time.perf_counter() - timer,
            configuration=config.model_dump(mode="json"),
            effective_compilation_config=effective,
            configuration_hash=config_digest(config_path),
            package_versions=package_versions(),
            input_hashes={config.source_circuit: sha256_file(source)},
            random_seed=config.compiler.get("seed"),
            mapping_complete=True,
            unknown_permutation_count=0,
        )
    except Exception as exc:
        message = sanitize_diagnostic(exc)
        report = CompilationReport(
            status="blocked" if isinstance(exc, RuntimeError) else "failed",
            backend=backend_descriptor,
            original=original,
            start_timestamp=start,
            end_timestamp=datetime.now(UTC),
            wall_clock_seconds=time.perf_counter() - timer,
            failure={
                "exception_type": type(exc).__name__,
                "sanitized_message": message,
                "stage": "target_configuration"
                if not device_name or descriptor is None
                else "compilation",
                "suggested_next_step": "Run devices, choose an exact compatible target, and retry compile-only validation.",
            },
            configuration=config.model_dump(mode="json"),
            effective_compilation_config=effective,
            configuration_hash=config_digest(config_path),
            package_versions=package_versions(),
            input_hashes={config.source_circuit: sha256_file(source)},
            random_seed=config.compiler.get("seed"),
            mapping_complete=False,
            unknown_permutation_count=98,
        )
    write_json(output_dir / "compilation_report.json", report)
    write_json(output_dir / "effective_compilation_config.json", effective)
    write_json(
        output_dir / "validation_result.json",
        report.validation
        or ValidationResult(
            passed=False,
            predicates={"compilation_completed": False},
            diagnostics=[report.failure["sanitized_message"] if report.failure else "Incomplete"],
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
            else f"Validation passed: {report.validation.passed if report.validation else False}\n"
        )
        + "\nImplicit swaps are disabled; unknown permutations block success. No job was submitted.\n"
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
    predicates: dict[str, bool | None] = {
        "compilation_succeeded": report.status == "success",
        "backend_validation_passed": report.validation.passed if report.validation else False,
        "mapping_complete": report.mapping_complete,
        "unknown_permutation_count_zero": report.unknown_permutation_count == 0,
        "hardware_not_attempted": True,
        "paid_resources_not_consumed": True,
    }
    result = ValidationResult(
        passed=all(predicates.values()),
        predicates=predicates,
        diagnostics=[]
        if all(predicates.values())
        else ["Compilation, mapping, or target validation remains incomplete"],
    )
    write_json(root / "results/compilation/validation_result.json", result)
    return result
