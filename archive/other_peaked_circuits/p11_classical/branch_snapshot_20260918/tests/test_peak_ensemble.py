from pathlib import Path

import pytest

from p12_recovery.peak.ensemble import enumerate_completions, reliability, summarize_samples


def _run(candidate: str, family: str) -> dict:
    return {"candidate": candidate, "bits": len(candidate), "margins": [0.8] * len(candidate), "method_family": family}


def test_single_family_never_locks_bits() -> None:
    result = reliability([_run("0101", "mps"), _run("0101", "mps")])
    assert set(bit["classification"] for bit in result["bits"]) == {"LIKELY"}


def test_independent_agreement_can_lock_bits() -> None:
    result = reliability([_run("0101", "mps"), _run("0101", "mpo")])
    assert set(bit["classification"] for bit in result["bits"]) == {"LOCKED"}


def test_joint_completion_is_bounded_and_ranked() -> None:
    result = enumerate_completions("0??", [1, 2], lambda value: value.count("1"))
    assert result[0]["candidate"] == "011"
    with pytest.raises(ValueError):
        enumerate_completions("0??", [1, 2], lambda _: 0, max_completions=2)


def test_sample_summary_is_answer_blind(tmp_path: Path) -> None:
    source = tmp_path / "samples.tsv"
    source.write_text("permuted\n010\n011\n")
    result = summarize_samples(["010", "011"], method_family="mps", run_id="r", source=source)
    assert result["candidate"] == "010"  # deterministic zero on a tie
    assert result["answer_blind"] is True
    assert "expected" not in result and "overlap" not in result
