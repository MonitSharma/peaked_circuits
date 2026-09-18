from __future__ import annotations

import pytest

from p12_recovery.mapping_validation import validation_patterns
from p12_recovery.nexus_results import parse_qir_result_records
from p12_recovery.provider_mapping import infer_labeled_qir_mapping


def case_payload(pattern: str, order: list[int]) -> str:
    rows = ["HEADER\tschema_id\tlabeled"]
    for _ in range(3):
        rows.append("START")
        rows.extend(f"OUTPUT\tRESULT\t{pattern[index]}\tm{index:03d}[0]" for index in order)
        rows.append("END\t0")
    return "\n".join(rows) + "\n"


@pytest.mark.parametrize("order", [list(range(98)), list(reversed(range(98))), [*range(1, 98), 0]])
def test_mapping_infers_unique_identity_reversal_and_displacement(order: list[int]) -> None:
    patterns = validation_patterns()
    parsed = {
        name: parse_qir_result_records(case_payload(pattern, order))
        for name, pattern in patterns.items()
    }
    report = infer_labeled_qir_mapping(parsed, patterns)
    assert report["resolved_positions"] == 98
    assert report["provider_result_order_verified"]
    by_logical = {entry["logical_qubit_index"]: entry for entry in report["entries"]}
    assert by_logical[0]["provider_result_position"] == order.index(0)
    assert by_logical[97]["provider_result_position"] == order.index(97)


def test_mapping_rejects_endpoint_swap() -> None:
    patterns = validation_patterns()
    order = list(range(98))
    parsed = {
        name: parse_qir_result_records(case_payload(pattern, order))
        for name, pattern in patterns.items()
    }
    broken = case_payload(patterns["q0"], order).replace("\t1\tm000[0]", "\t0\tm000[0]")
    parsed["q0"] = parse_qir_result_records(broken)
    with pytest.raises(ValueError, match="mismatch"):
        infer_labeled_qir_mapping(parsed, patterns)


def test_mapping_rejects_ambiguous_label() -> None:
    patterns = validation_patterns()
    order = list(range(98))
    parsed = {
        name: parse_qir_result_records(case_payload(pattern, order))
        for name, pattern in patterns.items()
    }
    parsed["all_zeros"] = parse_qir_result_records(
        case_payload(patterns["all_zeros"], order).replace("m097[0]", "unknown")
    )
    with pytest.raises(ValueError):
        infer_labeled_qir_mapping(parsed, patterns)
