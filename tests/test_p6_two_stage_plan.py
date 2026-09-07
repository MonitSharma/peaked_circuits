import json
from pathlib import Path


def test_p6_two_stage_plan_is_frozen_and_offline() -> None:
    root = Path(__file__).parents[1]
    protocol = json.loads((root / "hardware_campaign/p6_batch_001/protocol.json").read_text())
    assert protocol["status"] in {
        "READY_FOR_USER_SUBMISSION",
        "DISCOVERY_SUBMITTED_AWAITING_ANALYSIS",
        "DISCOVERY_REJECTED_QUOTA_AWAITING_REFRESH",
        "TWO_BATCHES_ANALYZED_NO_REPRODUCIBLE_CANDIDATE",
    }
    assert protocol["backend"] == "Helios-1"
    assert protocol["analysis"]["external_target_used_before_freeze"] is False
    assert protocol["analysis"]["quantum_advantage_claim"] is False
    assert [stage["shots"] for stage in protocol["stages"]] == [100, 100]
    assert [stage["max_cost_hqc"] for stage in protocol["stages"]] == [900.0, 900.0]
    assert protocol["operator_gate"]["discovery_must_complete_before_confirmation"] is True
    assert protocol["operator_gate"]["confirmation_auto_submit"] is False
    assert protocol["operator_gate"]["explicit_user_approval_required"] is True

    discovery = json.loads((root / "hardware_campaign/p6_batch_001/job_records/discovery.json").read_text())
    confirmation = json.loads((root / "hardware_campaign/p6_batch_001/job_records/confirmation.json").read_text())
    assert discovery["status"] in {"NOT_SUBMITTED", "SUBMITTED", "REJECTED_PREQUEUE", "ANALYZED"}
    assert confirmation["status"] == "NOT_SUBMITTED"
    if discovery["status"] in {"NOT_SUBMITTED", "REJECTED_PREQUEUE"}:
        assert discovery["job_id"] is None
    else:
        assert discovery["job_id"]
    assert confirmation["candidate_frozen_before_confirmation"] is False
    assert "explicitly approved" in confirmation["notes"]


def test_discovery_submitter_has_no_confirmation_path() -> None:
    root = Path(__file__).parents[1]
    submitter = (root / "tools/submit_p6_discovery.py").read_text()
    assert 'SHOTS = 100' in submitter
    assert 'MAX_COST = 900.0' in submitter
    assert "p6_physical_confirmation_100" not in submitter
    assert "confirmation" in submitter.lower()
