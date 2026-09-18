from scripts.p6_oracle_solver import errors_in_subset, flipped_query, overlap


def test_overlap_query_identity():
    baseline = "0101"
    target = "0110"
    assert overlap(baseline, target) == 2
    query = flipped_query(baseline, [1, 3])
    assert query == "0000"
    assert errors_in_subset(baseline, 2, [1, 3], overlap(query, target)) == 1


def test_single_bit_score_change_classifies_bit():
    baseline = "0101"
    target = "0110"
    baseline_score = overlap(baseline, target)
    assert overlap(flipped_query(baseline, [0]), target) == baseline_score - 1
    assert overlap(flipped_query(baseline, [2]), target) == baseline_score + 1
