from pathlib import Path

import pytest

from p12_recovery.p11_extraction import hamming, majority_candidate, parse_samples, wilson_interval


def test_majority_and_tie_are_explicit() -> None:
    samples = ["0" * 95 + suffix for suffix in ("010", "011", "000", "001")]
    candidate, ties = majority_candidate(samples)
    assert candidate[-3:] == "000"
    assert ties[-3:] == [False, True, True]


def test_hamming_validates_length() -> None:
    assert hamming("010", "011") == 1
    with pytest.raises(ValueError):
        hamming("0", "00")


def test_wilson_interval_contains_half() -> None:
    low, high = wilson_interval(50, 100)
    assert 0.40 < low < 0.5 < high < 0.60


def test_parser_rejects_malformed_sample(tmp_path: Path) -> None:
    path = tmp_path / "samples.tsv"
    path.write_text("raw\tpermuted\n0\t0\n")
    with pytest.raises(ValueError):
        parse_samples(path)
