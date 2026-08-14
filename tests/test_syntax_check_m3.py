from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from p12_recovery.hashing import sha256_file
from p12_recovery.models import QIRExportReport
from p12_recovery.nexus_syntax_check import (
    create_syntax_check_job,
    submit_validated_syntax_check,
)
from p12_recovery.syntax_check_guard import (
    NexusSyntaxCheckBlocked,
    assert_nexus_syntax_check_allowed,
)


def allowed(**overrides: Any) -> None:
    values: dict[str, Any] = {
        "submit_syntax_check": True,
        "environment": {"P12_ENABLE_NEXUS_SYNTAX_CHECK": "1"},
        "target": "Helios-1SC",
        "target_classification": "syntax_checker",
        "authenticated_discovery": True,
        "discovered_targets": {"Helios-1SC"},
        "qir_validation_passed": True,
        "logical_to_qir_mapping_verified": True,
        "expected_qir_hash": "abc",
        "actual_qir_hash": "abc",
        "validation_qir_hash": "abc",
        "artifact_git_commit": "commit",
        "current_git_commit": "commit",
        "artifact_git_dirty": False,
        "current_git_dirty": False,
        "current_dirty_is_generated_artifacts_only": False,
        "mapping_syntax_checks_passed": True,
        "interactive_confirmed": True,
    }
    values.update(overrides)
    assert_nexus_syntax_check_allowed(**values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"submit_syntax_check": False},
        {"environment": {}},
        {"target": "Helios-1"},
        {"target": "Helios-1E", "target_classification": "emulator"},
        {"target": "H2-1SC"},
        {"discovered_targets": set()},
        {"expected_qir_hash": "changed"},
        {"qir_validation_passed": False},
        {"artifact_git_dirty": True, "current_git_dirty": False},
        {"interactive_confirmed": False},
        {"mapping_syntax_checks_passed": False},
    ],
)
def test_syntax_check_guard_blocks_every_missing_condition(overrides: dict[str, Any]) -> None:
    with pytest.raises(NexusSyntaxCheckBlocked):
        allowed(**overrides)


def test_complete_helios_1sc_authorization_passes() -> None:
    allowed()


def test_only_new_generated_artifacts_may_make_clean_export_dirty() -> None:
    allowed(current_git_dirty=True, current_dirty_is_generated_artifacts_only=True)


class _FakeRef:
    def __init__(self, identifier: str, *, cost: float | None = None) -> None:
        self.id = identifier
        self.cost = cost

    def __str__(self) -> str:
        return "token=should-never-be-stored"


def test_mocked_nexus_submission_is_fixed_to_syntax_checker_and_sanitized(tmp_path: Path) -> None:
    qir = tmp_path / "results/qir/p12.ll"
    qir.parent.mkdir(parents=True)
    qir.write_text("verified textual qir")
    bitcode = qir.with_suffix(".bc")
    bitcode.write_bytes(b"BC verified bitcode")
    qir_hash, bitcode_hash = sha256_file(qir), sha256_file(bitcode)
    export = QIRExportReport(
        status="success",
        source_qasm_sha256="source-hash",
        source_qubits=98,
        source_operations=1,
        source_two_qubit_gates=0,
        source_measurements=0,
        transformed_operation_counts={"Measure": 98},
        transformed_operations=98,
        measurement_count=98,
        canonical_order="logical_q0_to_q97_left_to_right",
        qir_format="LLVM_IR_TEXT",
        qir_profile="BASE",
        qir_path="results/qir/p12.ll",
        qir_sha256=qir_hash,
        qir_size_bytes=qir.stat().st_size,
        qir_bitcode_path="results/qir/p12.bc",
        qir_bitcode_sha256=bitcode_hash,
        qir_bitcode_size_bytes=bitcode.stat().st_size,
        conversion_api="fixture",
        conversion_preflight_passed=True,
        logical_to_qir_mapping_verified=True,
    )
    seen: dict[str, Any] = {}

    class Models:
        @staticmethod
        def HeliosConfig(*, system_name: str) -> SimpleNamespace:
            seen["system_name"] = system_name
            return SimpleNamespace(system_name=system_name)

    fake = SimpleNamespace(
        projects=SimpleNamespace(get_or_create=lambda **_: _FakeRef("safe-project")),
        qir=SimpleNamespace(upload=lambda **_: _FakeRef("safe-artifact")),
        models=Models,
        start_execute_job=lambda **kwargs: (
            seen.update({"backend": kwargs["backend_config"].system_name})
            or _FakeRef("safe-job")
        ),
        jobs=SimpleNamespace(
            wait_for=lambda *_args, **_kwargs: "COMPLETED",
            results=lambda *_args, **_kwargs: [_FakeRef("safe-result", cost=0.0)],
        ),
    )
    report = submit_validated_syntax_check(
        tmp_path,
        qir_path=qir,
        export=export,
        project_name="p12-helios-recovery",
        timeout_seconds=1,
        client_module=fake,
    )
    assert report.status == "passed"
    assert seen == {"system_name": "Helios-1SC", "backend": "Helios-1SC"}
    stored = "\n".join(
        path.read_text(errors="replace")
        for path in (tmp_path / "results/nexus/syntax_check").glob("*")
        if path.is_file()
    )
    assert "should-never-be-stored" not in stored
    assert "safe-project" in stored and "safe-job" in stored
    assert '"hqcs_used": false' in stored


def test_start_execute_job_does_not_require_public_language_enum(
    monkeypatch,
) -> None:
    captured = {}

    def fake_start_execute_job(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "p12_recovery.nexus_syntax_check.qnx.start_execute_job",
        fake_start_execute_job,
    )

    # Call the internal job-creation helper with fixture refs/config.
    create_syntax_check_job(
        qir_ref=object(),
        backend_config=object(),
        project_ref=object(),
        job_name="test-syntax-check",
    )

    assert "language" not in captured
    assert captured["n_shots"] == [1]


def test_qnexus_language_is_not_assumed_on_models_namespace() -> None:
    import qnexus as qnx

    # The implementation must not depend on qnx.models.Language.
    assert not hasattr(qnx.models, "Language")
