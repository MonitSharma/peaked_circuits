import pytest

from p12_recovery.recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    score_candidate,
    weighted_observed_medoid,
)


def test_clean_recovery_and_determinism() -> None:
    counts = {"0000": 8, "0001": 1, "0010": 1}
    assert most_frequent_string(counts).canonical_bitstring == "0000"
    assert bitwise_majority_string(counts).canonical_bitstring == "0000"
    assert weighted_observed_medoid(counts).canonical_bitstring == "0000"
    assert cluster_consensus(counts, distance_threshold=0.3).canonical_bitstring == "0000"
    assert (
        most_frequent_string(counts).canonical_bitstring
        == most_frequent_string(counts).canonical_bitstring
    )


def test_tie_medoid_cluster_and_agreement() -> None:
    tie = bitwise_majority_string({"00": 1, "11": 1})
    assert tie.canonical_bitstring == "00"
    assert tie.confidence["uncertain_positions"] == [0, 1]
    assert weighted_observed_medoid({"00": 1, "01": 1}).canonical_bitstring == "00"
    clustered = cluster_consensus({"000": 5, "001": 3, "111": 2}, distance_threshold=0.34)
    assert clustered.canonical_bitstring == "000"
    agreement = method_agreement(
        [most_frequent_string({"00": 2}), bitwise_majority_string({"01": 2})]
    )
    assert agreement["disagreement_positions"] == [1]


def test_score_and_invalid_strings() -> None:
    target = "0" * 98
    score = score_candidate("1" + "0" * 97, target)
    assert score.correct_bits == 97 and score.incorrect_indices == (0,)
    with pytest.raises(ValueError):
        most_frequent_string({"0x": 1})
