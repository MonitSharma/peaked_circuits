from pathlib import Path

import pytest

from p12_recovery.batch_analysis import analyze_batch, merge_batch_counts
from p12_recovery.campaign import BatchRole, CampaignStore, operational_max_cost
from p12_recovery.candidate_freeze import validate_candidate
from p12_recovery.nexus_hardware import PhysicalSubmissionDisabled, dry_run_hardware_batch


def _artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    paths = [tmp_path / name for name in ("source.qasm", "p12.ll", "p12.bc")]
    for path in paths:
        path.write_text("artifact")
    return tuple(paths)  # type: ignore[return-value]


def test_campaign_is_append_safe_and_duplicate_guarded(tmp_path: Path) -> None:
    source, qir, bitcode = _artifacts(tmp_path)
    store = CampaignStore(tmp_path)
    state = store.initialize(source=source, qir=qir, bitcode=bitcode, predicted_hqc=2742)
    batch = store.create_batch(state, role=BatchRole.DISCOVERY, shots=400, max_cost=2842)
    assert batch.batch_id == "batch_001"
    with pytest.raises(ValueError, match="Batch already exists"):
        state.next_batch_number = 1
        store.create_batch(state, role=BatchRole.CONFIRMATION, shots=400)


def test_dry_run_never_calls_provider(tmp_path: Path) -> None:
    from p12_recovery.nexus_hardware import HardwarePreflightReport

    report = HardwarePreflightReport(batch_id="batch_001", target="Helios-1", requested_shots=400, predicted_hqc=2742, recommended_max_cost=2842, checks={"ready": True})
    rendered = dry_run_hardware_batch(tmp_path, report)
    assert rendered["provider_call_made"] is False
    assert rendered["max_cost"] == 2842


def test_cost_cap_and_candidate_validation() -> None:
    assert operational_max_cost(2742) == 2842
    assert len(validate_candidate("0" * 98)) == 98
    with pytest.raises(ValueError):
        validate_candidate("0" * 97)


def test_batch_analysis_is_target_blind_and_dictionary_order_invariant() -> None:
    first = {"0" * 98: 8, "1" * 98: 2}
    second = {"1" * 98: 2, "0" * 98: 8}
    assert merge_batch_counts([first]) == merge_batch_counts([second])
    report = analyze_batch(first, seed=12)
    assert "external_target" not in report
    assert report["shots"] == 10


def test_physical_submission_guard_requires_explicit_authorization() -> None:
    from p12_recovery.nexus_hardware import HardwarePreflight, assert_hardware_preflight

    preflight = HardwarePreflight(target="Helios-1", target_type="hardware", qubit_capacity=98, source_qasm_sha256="0" * 64, qir_sha256="1" * 64, bitcode_sha256="2" * 64, syntax_check_passed=True, mapping_verified=True, predicted_hqc=100, requested_shots=1, max_cost=200, protocol_frozen=True, campaign_valid=True, no_active_job=True)
    with pytest.raises(PhysicalSubmissionDisabled):
        assert_hardware_preflight(preflight)
