import pytest

from p12_recovery.bit_ordering import (
    build_measurement_mapping,
    canonical_to_raw_bitstring,
    raw_bitstring_to_canonical,
)


def test_known_patterns_msb_left() -> None:
    kwargs = {
        "logical_to_classical": {i: i for i in range(5)},
        "sdk_string_order": "msb_left",
        "register_layout": [{"name": "c", "classical_indices": [0, 1, 2, 3, 4]}],
    }
    assert raw_bitstring_to_canonical("00001", **kwargs) == "10000"  # q0=1
    assert raw_bitstring_to_canonical("10000", **kwargs) == "00001"  # highest=1
    assert raw_bitstring_to_canonical("01010", **kwargs) == "01010"  # alternating
    assert raw_bitstring_to_canonical("00101", **kwargs) == "10100"  # non-palindrome


def test_multiple_registers_leading_zeros_roundtrip() -> None:
    layout = [
        {"name": "a", "classical_indices": [0, 1]},
        {"name": "b", "classical_indices": [2, 3, 4]},
    ]
    mapping = build_measurement_mapping(
        logical_to_classical={i: i for i in range(5)},
        sdk_string_order="msb_left",
        register_layout=layout,
    )
    raw = canonical_to_raw_bitstring("00101", mapping)
    assert len(raw) == 5
    assert (
        raw_bitstring_to_canonical(
            raw,
            logical_to_classical={i: i for i in range(5)},
            sdk_string_order="msb_left",
            register_layout=layout,
        )
        == "00101"
    )


@pytest.mark.parametrize("mapping", [{0: 0, 2: 1}, {0: 0, 1: 0}])
def test_invalid_or_duplicate_mapping(mapping: dict[int, int]) -> None:
    with pytest.raises(ValueError):
        build_measurement_mapping(
            logical_to_classical=mapping,
            sdk_string_order="msb_left",
            register_layout=[{"classical_indices": [0, 1]}],
        )


def test_ambiguous_or_bad_string_fails() -> None:
    with pytest.raises(ValueError):
        raw_bitstring_to_canonical(
            "0x",
            logical_to_classical={0: 0, 1: 1},
            sdk_string_order="msb_left",
            register_layout=[{"classical_indices": [0, 1]}],
        )
    with pytest.raises(ValueError):
        raw_bitstring_to_canonical(
            "01",
            logical_to_classical={0: 0, 1: 1},
            sdk_string_order="unknown",
            register_layout=[{"classical_indices": [0, 1]}],
        )
