from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from p12_recovery.hashing import sha256_file
from p12_recovery.mapping_validation import validation_patterns
from p12_recovery.models import QIRExportReport, QIROutputMapping
from p12_recovery.qir_export import export_mapping_qir_cases, export_p12_qir
from p12_recovery.qir_validation import validate_qir_artifact


@pytest.fixture(scope="module")
def exported_p12(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, QIRExportReport]:
    root = tmp_path_factory.mktemp("qir-export")
    source_dir = root / "circuits/original"
    source_dir.mkdir(parents=True)
    repository = Path(__file__).resolve().parents[1]
    source_name = "peaked_circuit_P12_Hqap_98x2457.qasm"
    shutil.copyfile(repository / "circuits/original" / source_name, source_dir / source_name)
    shutil.copyfile(repository / "circuits/original/SHA256SUMS", source_dir / "SHA256SUMS")
    output = root / "results/qir/p12.ll"
    report = export_p12_qir(root, source_dir / source_name, output)
    return root, report


def test_p12_qir_export_is_complete(exported_p12: tuple[Path, QIRExportReport]) -> None:
    root, report = exported_p12
    assert report.source_qasm_sha256 == sha256_file(
        root / "circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm"
    )
    assert report.measurement_count == 98
    assert report.qir_size_bytes > 0
    assert report.omitted_operation_count == 0
    mapping = QIROutputMapping.model_validate_json(
        (root / "results/qir/qir_output_mapping.json").read_text()
    )
    assert len(mapping.entries) == 98
    assert mapping.logical_to_qir_mapping_verified
    assert not mapping.provider_result_order_verified
    assert all(entry.provider_result_position is None for entry in mapping.entries)


def test_p12_qir_is_deterministic(exported_p12: tuple[Path, QIRExportReport]) -> None:
    root, first = exported_p12
    second = export_p12_qir(
        root,
        root / "circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm",
        root / "results/second/p12.ll",
    )
    assert second.qir_sha256 == first.qir_sha256
    assert second.qir_bitcode_sha256 == first.qir_bitcode_sha256


def test_strict_qir_validation_passes(exported_p12: tuple[Path, QIRExportReport]) -> None:
    root, _ = exported_p12
    result = validate_qir_artifact(root, root / "results/qir/p12.ll")
    assert result.status == "passed"
    assert result.required_num_qubits == result.required_num_results == 98
    assert result.measurement_call_count == result.result_output_count == 98
    assert result.logical_to_qir_mapping_verified
    assert result.fixture_semantic_validation_level == "structural_only_no_local_qir_execution_engine"


@pytest.mark.parametrize(
    ("mutation", "failed_check"),
    [
        (lambda text: "", "file_nonempty"),
        (
            lambda text: text.replace('"required_num_qubits"="98"', '"required_num_qubits"="97"'),
            "resource_counts_match",
        ),
        (
            lambda text: text.replace(
                "call void @__quantum__rt__result_record_output", "; removed output\n; call void @__quantum__rt__result_record_output", 1
            ),
            "result_output_count_matches",
        ),
        (
            lambda text: text + "\n; /" + "Users/example/private\n",
            "no_absolute_local_paths",
        ),
        (lambda text: text + "\n; token=fixture-secret\n", "no_credential_like_material"),
    ],
)
def test_qir_validation_rejects_mutations(
    exported_p12: tuple[Path, QIRExportReport],
    mutation: Callable[[str], str],
    failed_check: str,
) -> None:
    root, _ = exported_p12
    original = root / "results/qir/p12.ll"
    changed = root / f"results/qir/{failed_check}.ll"
    changed.write_text(mutation(original.read_text()))
    result = validate_qir_artifact(
        root,
        changed,
        export_report_path=root / "results/qir/qir_export_report.json",
        write_report=False,
    )
    assert result.status == "failed"
    assert not result.checks[failed_check]


def test_changed_hash_fails(exported_p12: tuple[Path, QIRExportReport]) -> None:
    root, _ = exported_p12
    changed = root / "results/qir/changed.ll"
    changed.write_text((root / "results/qir/p12.ll").read_text() + "\n; changed\n")
    result = validate_qir_artifact(
        root,
        changed,
        export_report_path=root / "results/qir/qir_export_report.json",
        write_report=False,
    )
    assert not result.checks["hash_matches_export"]


def test_all_mapping_qir_cases_export(tmp_path: Path) -> None:
    report = export_mapping_qir_cases(tmp_path)
    expected = validation_patterns()
    assert report.status == "passed"
    assert report.passed_cases == report.total_cases == 6
    assert report.reversal_sensitive
    assert [case.case_name for case in report.cases] == list(expected)
    for case in report.cases:
        payload = json.loads(
            (tmp_path / "results/qir/mapping_cases" / case.case_name / "expected_output.json").read_text()
        )
        assert payload["expected_canonical_string"] == expected[case.case_name]
        assert (tmp_path / case.qir_path).is_file()
    assert expected["q0"][0] == "1" and expected["q0"][-1] == "0"
    assert expected["q97"][0] == "0" and expected["q97"][-1] == "1"
    assert expected["non_palindromic_blocks"] != expected["non_palindromic_blocks"][::-1]
