from pathlib import Path

import pytest

from p12_recovery.bit_ordering import build_measurement_mapping
from p12_recovery.models import MeasurementMapping, ProviderRawResult
from p12_recovery.provider_results import normalize_provider_result, persist_imported_result


def identity_mapping() -> MeasurementMapping:
    return build_measurement_mapping(
        logical_to_classical={i: i for i in range(98)},
        sdk_string_order="lsb_left",
        register_layout=[{"name": "result", "classical_indices": list(range(98))}],
    )


def raw_result(bitstring: str, shots: int = 3) -> ProviderRawResult:
    return ProviderRawResult(
        device_name="fixture-emulator",
        job_id="existing-job-1",
        requested_shots=shots,
        returned_shots=shots,
        raw_counts={bitstring: shots},
        raw_shots=[list(bitstring) for _ in range(shots)],
        raw_register_layout=[{"name": "result", "classical_indices": list(range(98))}],
        raw_result_order="lsb_left",
    )


def test_aggregated_and_shot_import_are_canonical() -> None:
    prepared = "1" + "0" * 97
    canonical = normalize_provider_result(raw_result(prepared), identity_mapping())
    assert canonical.canonical_counts == {prepared: 3}
    assert canonical.canonical_shots == [prepared] * 3
    assert canonical.all_outputs_length_98


def test_provider_import_rejects_width_and_incomplete_mapping() -> None:
    with pytest.raises(ValueError, match="width"):
        normalize_provider_result(raw_result("0" * 97), identity_mapping())
    incomplete = identity_mapping().model_copy(update={"complete": False})
    with pytest.raises(ValueError, match="complete"):
        normalize_provider_result(raw_result("0" * 98), incomplete)


def test_persist_separates_raw_and_canonical(tmp_path: Path) -> None:
    prepared = "0" * 98
    outputs = persist_imported_result(
        tmp_path,
        raw_result(prepared),
        identity_mapping(),
        bootstrap_replicates=2,
    )
    assert outputs["raw"].is_file()
    assert outputs["counts"].is_file()
    assert "data/provider_raw" in outputs["raw"].as_posix()
    assert "data/canonical" in outputs["counts"].as_posix()
    assert outputs["recovery"].is_file()
