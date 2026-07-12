import json
from datetime import UTC, datetime
from pathlib import Path

import p12_recovery.readiness as readiness
from p12_recovery.bit_ordering import build_measurement_mapping
from p12_recovery.hashing import sha256_file
from p12_recovery.models import (
    BackendDescriptor,
    CompilationReport,
    MappingValidationCase,
    MappingValidationReport,
    ReadinessState,
    ValidationResult,
)
from p12_recovery.reporting import write_json


def test_no_full_experiment_state_exists() -> None:
    assert "READY_FOR_FULL_EXPERIMENT" not in {state.value for state in ReadinessState}


def test_milestone_2_evidence_never_reaches_hardware_state(
    tmp_path: Path, monkeypatch: object
) -> None:
    qasm = tmp_path / "circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm"
    qasm.parent.mkdir(parents=True)
    qasm.write_text("OPENQASM 2.0;")
    (qasm.parent / "SHA256SUMS").write_text(f"{sha256_file(qasm)}  {qasm.name}\n")
    compilation = CompilationReport(
        status="success",
        backend=BackendDescriptor(
            provider="quantinuum",
            device_name="fixture-98",
            qubit_capacity=98,
            has_at_least_98_qubits=True,
            p12_compatible=True,
        ),
        original={"source_hash": sha256_file(qasm)},
        compiled={"compiled_qasm_hash": "abc", "qubit_count": 98},
        validation=ValidationResult(passed=True, predicates={"all": True}),
        start_timestamp=datetime.now(UTC),
        end_timestamp=datetime.now(UTC),
        wall_clock_seconds=0,
        configuration={},
        package_versions={"pytket": "fixture"},
        git_commit="fixture-commit",
        mapping_complete=True,
        unknown_permutation_count=0,
    )
    write_json(tmp_path / "results/compilation/compilation_report.json", compilation)
    mapping = build_measurement_mapping(
        logical_to_classical={i: i for i in range(98)},
        sdk_string_order="lsb_left",
        register_layout=[{"name": "out", "classical_indices": list(range(98))}],
    )
    write_json(tmp_path / "results/compilation/measurement_mapping.json", mapping)
    cases = [
        MappingValidationCase(
            case_name=str(i),
            prepared_logical_string="0" * 98,
            mapping_correct=True,
            status="passed",
        )
        for i in range(6)
    ]
    write_json(
        tmp_path / "results/mapping_validation/mapping_validation_report.json",
        MappingValidationReport(
            status="passed", mode="emulator", cases=cases, passed_cases=6, total_cases=6
        ),
    )
    synthetic = tmp_path / "results/synthetic/synthetic_report.json"
    synthetic.parent.mkdir(parents=True)
    synthetic.write_text("{}")
    cost = tmp_path / "results/cost/cost_estimate.json"
    cost.parent.mkdir(parents=True)
    cost.write_text('{"status":"supported"}')
    protocol = tmp_path / "results/protocol/protocol_freeze.json"
    protocol.parent.mkdir(parents=True)
    protocol.write_text(
        json.dumps(
            {
                "status": "frozen",
                "configuration": {
                    "primary_analysis": {"method": "bitwise_majority"},
                    "tracker_protocol_confirmed": True,
                },
            }
        )
    )
    monkeypatch.setattr(readiness, "_fixture_checks", lambda _: True)  # type: ignore[attr-defined]
    monkeypatch.setattr(readiness, "_hardware_guard_self_check", lambda: True)  # type: ignore[attr-defined]
    monkeypatch.setattr(readiness, "_commit_tagged", lambda _root, _commit: True)  # type: ignore[attr-defined]
    monkeypatch.setattr(readiness, "git_state", lambda _: ("fixture-commit", False))  # type: ignore[attr-defined]
    report = readiness.build_readiness(tmp_path)
    assert report.state == "READY_FOR_COMPILE_ONLY"
    assert not report.ready
    assert "READY_FOR_HARDWARE_SMOKE_TEST" not in {state.value for state in ReadinessState}


def test_missing_evidence_is_not_smoke_ready(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr(readiness, "_fixture_checks", lambda _: False)  # type: ignore[attr-defined]
    report = readiness.build_readiness(tmp_path)
    assert report.state == "NOT_READY"
    assert not report.ready
