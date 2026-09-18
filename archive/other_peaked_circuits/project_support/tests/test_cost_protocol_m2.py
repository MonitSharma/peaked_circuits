from pathlib import Path

import pytest

import p12_recovery.protocol as protocol_module
from p12_recovery.cost_estimation import estimate_costs
from p12_recovery.protocol import ProtocolFreezeBlocked, freeze_protocol


def test_cost_estimation_records_unsupported_without_formula(tmp_path: Path) -> None:
    report = estimate_costs(tmp_path, "fixture-target", [20, 100])
    assert report.status == "unsupported"
    assert report.manual_action_required
    assert all(item.estimated_hqcs is None for item in report.estimates)
    assert (tmp_path / "results/cost/cost_estimate.json").is_file()


def test_protocol_freeze_rejects_dirty_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "experiment.yaml"
    config.write_text("status: draft\n")
    monkeypatch.setattr(protocol_module, "git_state", lambda _: ("commit", True))
    with pytest.raises(ProtocolFreezeBlocked, match="dirty"):
        freeze_protocol(tmp_path, config)


def test_protocol_freeze_lists_missing_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "experiment.yaml"
    config.write_text(
        """status: draft
circuit: {source_hash: null}
primary_analysis: {method: bitwise_majority, tie_policy: deterministic_zero}
primary_shots: 2000
pilot_shots: 100
smoke_test_shots: 20
"""
    )
    monkeypatch.setattr(protocol_module, "git_state", lambda _: ("commit", False))
    with pytest.raises(ProtocolFreezeBlocked, match="source_hash_exists"):
        freeze_protocol(tmp_path, config)
