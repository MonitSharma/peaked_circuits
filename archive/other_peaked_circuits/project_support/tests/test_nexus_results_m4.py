from __future__ import annotations

import pytest

from p12_recovery.nexus_results import (
    parse_provider_result,
    parse_qir_result_records,
    validate_result_shape,
)


def payload(width: int = 98, *, reverse: bool = False, duplicate: bool = False) -> str:
    labels = [f"m{i:03d}[0]" for i in range(width)]
    if reverse:
        labels.reverse()
    if duplicate:
        labels[-1] = labels[0]
    rows = ["HEADER\tschema_id\tlabeled", "START"]
    rows.extend(f"OUTPUT\tRESULT\t{i % 2}\t{label}" for i, label in enumerate(labels))
    rows.append("END\t0")
    return "\n".join(rows) + "\n"


def test_parse_labeled_qir_preserves_fields_and_leading_zero() -> None:
    parsed = parse_qir_result_records(payload())
    validate_result_shape(parsed)
    assert parsed.shot_count == 1
    assert parsed.values[0].provider_name == "m000[0]"
    assert parsed.values[0].bit_value == 0
    assert parsed.values[-1].provider_index == 97


def test_parser_accepts_named_register_arrays_without_insertion_order_dependency() -> None:
    parsed = parse_provider_result({"b": [1, 0], "a": [0, 1]})
    assert [value.provider_name for value in parsed.values] == ["a", "a", "b", "b"]


@pytest.mark.parametrize(
    "bad",
    [
        "START\nOUTPUT\tRESULT\t2\tm000[0]\nEND\t0\n",
        "OUTPUT\tRESULT\t0\tm000[0]\n",
        "START\nOUTPUT\tRESULT\t0\nEND\t0\n",
    ],
)
def test_parser_rejects_malformed_or_nonbinary_records(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_qir_result_records(bad)


def test_shape_rejects_fewer_more_and_duplicate_fields() -> None:
    for bad in (payload(97), payload(99), payload(98, duplicate=True)):
        with pytest.raises(ValueError):
            validate_result_shape(parse_qir_result_records(bad))


def test_reversed_provider_fields_are_preserved() -> None:
    parsed = parse_qir_result_records(payload(reverse=True))
    validate_result_shape(parsed)
    assert parsed.values[0].provider_name == "m097[0]"
