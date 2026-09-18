import pytest

from p12_recovery.peak.portal_mapping import (
    logical_q0_first_to_portal,
    portal_to_logical_q0_first,
    validate_p9_control,
)


def test_non_palindromic_mapping_round_trip() -> None:
    permutation = [2, 0, 3, 1]
    assert logical_q0_first_to_portal("1001", permutation) == "0110"
    assert portal_to_logical_q0_first("0110", permutation) == "1001"


def test_p9_control_gate() -> None:
    result = validate_p9_control("0101", "0101", [0, 1, 2, 3])
    assert result["status"] == "PASS"


def test_mapping_rejects_non_permutation() -> None:
    with pytest.raises(ValueError):
        logical_q0_first_to_portal("010", [0, 0, 1])
