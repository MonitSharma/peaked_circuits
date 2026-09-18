from p12_recovery.bootstrap import bootstrap_recovery, prefix_shot_scaling, resampled_shot_scaling
from p12_recovery.recovery import bitwise_majority_string


def test_reproducible_dimensions_and_clean_case() -> None:
    counts = {"0000": 20}
    first = bootstrap_recovery(counts, bitwise_majority_string, replicates=10, seed=7)
    second = bootstrap_recovery(counts, bitwise_majority_string, replicates=10, seed=7)
    assert first.model_dump(exclude={"created_at"}) == second.model_dump(exclude={"created_at"})
    assert len(first.per_bit_selection_probability) == 4
    assert first.stable_bits == 4 and first.exact_match_stability == 1


def test_unstable_and_scaling_labels() -> None:
    report = bootstrap_recovery(
        {"00": 10, "11": 10}, bitwise_majority_string, replicates=40, seed=3
    )
    assert report.unstable_bits > 0
    resampled = resampled_shot_scaling(
        {"00": 10, "01": 5}, bitwise_majority_string, [5, 10], repeats=3, seed=2
    )
    assert all(row["analysis_type"] == "resampled_shot_scaling" for row in resampled)
    prefix = prefix_shot_scaling(["00"] * 4 + ["01"], bitwise_majority_string, [2, 5, 10])
    assert [row["shots"] for row in prefix] == [2, 5]
