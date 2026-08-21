from pathlib import Path

import pytest

from p12_recovery.batch_analysis import analyze_batch, merge_batch_counts
from p12_recovery.campaign import BatchRole, BatchStatus, CampaignStore, operational_max_cost
from p12_recovery.candidate_freeze import validate_candidate
from p12_recovery.nexus_hardware import (
    HardwarePreflight,
    HardwarePreflightReport,
    PhysicalSubmissionDisabled,
    dry_run_hardware_batch,
    retrieve_hardware_batch,
    submit_hardware_batch,
)


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
    from p12_recovery.nexus_hardware import assert_hardware_preflight

    preflight = HardwarePreflight(target="Helios-1", target_type="hardware", qubit_capacity=98, source_qasm_sha256="0" * 64, qir_sha256="1" * 64, bitcode_sha256="2" * 64, syntax_check_passed=True, mapping_verified=True, predicted_hqc=100, requested_shots=1, max_cost=200, protocol_frozen=True, campaign_valid=True, no_active_job=True)
    with pytest.raises(PhysicalSubmissionDisabled):
        assert_hardware_preflight(preflight)


def test_submission_crash_window_stays_pending_and_never_resubmits(tmp_path: Path) -> None:
    source, qir, bitcode = _artifacts(tmp_path)
    (tmp_path / "results/qir").mkdir(parents=True)
    (tmp_path / "results/qir/p12.bc").write_bytes(bitcode.read_bytes())
    store = CampaignStore(tmp_path)
    state = store.initialize(source=source, qir=qir, bitcode=bitcode, predicted_hqc=100)
    batch = store.create_batch(state, role=BatchRole.DISCOVERY, shots=1, max_cost=200)
    preflight = HardwarePreflight(target="Helios-1", target_type="hardware", qubit_capacity=98, source_qasm_sha256=state.source_qasm_sha256, qir_sha256=state.qir_sha256, bitcode_sha256=state.qir_bitcode_sha256, syntax_check_passed=True, mapping_verified=True, predicted_hqc=100, requested_shots=1, max_cost=200, protocol_frozen=True, campaign_valid=True, no_active_job=True)

    class Projects:
        def get_or_create(self, **_: object) -> str:
            return "project"

    class Qir:
        def upload(self, **_: object) -> str:
            return "artifact"

    class Models:
        class HeliosConfig:
            def __init__(self, **_: object) -> None:
                pass

    class FailingNexus:
        projects = Projects()
        qir = Qir()
        models = Models()

        @staticmethod
        def start_execute_job(**_: object) -> None:
            raise ConnectionError("lost after provider accepted request")

    with pytest.raises(ConnectionError):
        submit_hardware_batch(tmp_path, state, batch.batch_id, preflight=preflight, execute_hardware=True, environment={"P12_ENABLE_PHYSICAL_HELIOS": "1", "P12_CONFIRM_PAID_EXECUTION": "I_UNDERSTAND_THIS_MAY_CONSUME_HQC"}, interactive_confirmed=True, client_module=FailingNexus())
    assert CampaignStore(tmp_path).load().batches[batch.batch_id].status.value == "SUBMISSION_PENDING"
    with pytest.raises(PhysicalSubmissionDisabled, match="submitted/active"):
        submit_hardware_batch(tmp_path, CampaignStore(tmp_path).load(), batch.batch_id, preflight=preflight, execute_hardware=True, environment={"P12_ENABLE_PHYSICAL_HELIOS": "1", "P12_CONFIRM_PAID_EXECUTION": "I_UNDERSTAND_THIS_MAY_CONSUME_HQC"}, interactive_confirmed=True, client_module=FailingNexus())


def test_retrieval_reconstructs_job_ref_and_persists_provenance(tmp_path: Path) -> None:
    source, qir, bitcode = _artifacts(tmp_path)
    store = CampaignStore(tmp_path)
    state = store.initialize(source=source, qir=qir, bitcode=bitcode)
    batch = store.create_batch(state, role=BatchRole.DISCOVERY, shots=4, max_cost=100)
    store.update_batch(state, batch.batch_id, status=BatchStatus.SUBMITTED, execution_job_ref="job-1")

    class Result:
        id = "result-1"
        n_shots = 3
        cost = 12

        def download_result(self) -> dict[str, int]:
            return {"000": 3}

        def download_backend_info(self) -> dict[str, str]:
            return {"device": "Helios-1"}

        def get_input(self) -> bytes:
            return b"qir"

    class Jobs:
        def get(self, *, id: str) -> object:
            assert id == "job-1"
            return "JOB_REF_OBJECT"

        def results(self, job: object, *, allow_incomplete: bool = False) -> list[Result]:
            assert job == "JOB_REF_OBJECT"
            assert allow_incomplete is False
            return [Result()]

    class FakeNexus:
        jobs = Jobs()

    directory = retrieve_hardware_batch(tmp_path, CampaignStore(tmp_path).load(), batch.batch_id, client_module=FakeNexus())
    assert (directory / "job.json").is_file()
    assert (directory / "raw_result.json").is_file()
    assert (directory / "backend_info.json").is_file()
    assert (directory / "submitted_input.bc").is_file()
    assert (directory / "SHA256SUMS").is_file()
    assert CampaignStore(tmp_path).load().batches[batch.batch_id].returned_shots == 3
