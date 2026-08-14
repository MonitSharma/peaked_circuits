from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .nexus_results import ParsedProviderResult, validate_result_shape

_LABEL = re.compile(r"^m(?P<index>\d{3})\[0\]$")
_CONSTANT = re.compile(r'^@(?P<id>\d+) = .*c"(?P<label>m\d{3}\[0\])\\00"$', re.MULTILINE)
_OUTPUT_CALL = re.compile(r"result_record_output\([^\n]*ptr @(?P<id>\d+)\)")


def qir_declared_result_layout(path: Path) -> list[str]:
    """Return labels in explicit QIR result_record_output call order."""
    text = path.read_text()
    labels = {match.group("id"): match.group("label") for match in _CONSTANT.finditer(text)}
    layout = [labels[match.group("id")] for match in _OUTPUT_CALL.finditer(text)]
    if len(layout) != 98 or len(set(layout)) != 98:
        raise ValueError(f"QIR does not declare 98 unique labeled result outputs: {path}")
    return layout


def majority_by_field(
    parsed: ParsedProviderResult, *, minimum_majority_fraction: float
) -> tuple[dict[str, int], dict[str, float], list[str]]:
    grouped: dict[str, list[int]] = {}
    for value in parsed.values:
        grouped.setdefault(value.provider_name, []).append(value.bit_value)
    majority: dict[str, int] = {}
    confidence: dict[str, float] = {}
    inconsistent: list[str] = []
    for name, bits in grouped.items():
        counts = Counter(bits)
        bit, count = counts.most_common(1)[0]
        fraction = count / len(bits)
        if fraction < minimum_majority_fraction:
            raise ValueError(f"Ambiguous majority for provider field {name}: {fraction:.3f}")
        majority[name] = bit
        confidence[name] = fraction
        if len(counts) > 1:
            inconsistent.append(name)
    return majority, confidence, inconsistent


def infer_labeled_qir_mapping(
    parsed_cases: dict[str, ParsedProviderResult],
    expected_cases: dict[str, str],
    *,
    minimum_majority_fraction: float = 0.67,
    expected_provider_layouts: dict[str, list[str]] | None = None,
    output_mapping_layout: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve labeled Nexus QIR fields and validate them across deterministic cases."""
    if set(parsed_cases) != set(expected_cases):
        raise ValueError("Parsed and expected mapping-case sets differ")
    first_layout: tuple[str, ...] | None = None
    case_reports: dict[str, Any] = {}
    observed_by_case: dict[str, dict[str, int]] = {}
    for name, parsed in parsed_cases.items():
        validate_result_shape(parsed)
        shot_zero = sorted(
            (value for value in parsed.values if value.shot_index == 0),
            key=lambda value: value.provider_index if value.provider_index is not None else -1,
        )
        current_layout = tuple(value.provider_name for value in shot_zero)
        if expected_provider_layouts is not None:
            if current_layout != tuple(expected_provider_layouts[name]):
                raise ValueError(
                    f"Provider field layout differs from declared QIR order for {name}"
                )
        elif first_layout is None:
            first_layout = current_layout
        elif current_layout != first_layout:
            raise ValueError(f"Provider field layout differs for case {name}")
        majority, fractions, inconsistent = majority_by_field(
            parsed, minimum_majority_fraction=minimum_majority_fraction
        )
        observed_by_case[name] = majority
        canonical_bits = ["?"] * 98
        for field, bit in majority.items():
            match = _LABEL.fullmatch(field)
            if match is None:
                raise ValueError(f"Unrecognized QIR result label: {field}")
            index = int(match.group("index"))
            if not 0 <= index < 98 or canonical_bits[index] != "?":
                raise ValueError(f"Invalid or duplicate QIR result label: {field}")
            canonical_bits[index] = str(bit)
        canonical_string = "".join(canonical_bits)
        passed = canonical_string == expected_cases[name]
        case_reports[name] = {
            "status": "passed" if passed else "failed",
            "canonical_output": canonical_string,
            "expected_output": expected_cases[name],
            "minimum_field_majority_fraction": min(fractions.values()),
            "inconsistent_fields": inconsistent,
            "provider_layout": list(current_layout),
            "layout_matches_declared_qir": expected_provider_layouts is not None,
        }
        if not passed:
            raise ValueError(f"Deterministic output mismatch for {name}")
    layout = tuple(output_mapping_layout) if output_mapping_layout is not None else first_layout
    if layout is None:
        raise ValueError("No provider output mapping layout was supplied")
    entries: list[dict[str, Any]] = []
    seen_indices: set[int] = set()
    for provider_position, field in enumerate(layout):
        match = _LABEL.fullmatch(field)
        if match is None:
            raise ValueError(f"Unrecognized QIR result label: {field}")
        canonical = int(match.group("index"))
        if canonical in seen_indices:
            raise ValueError(f"Duplicate canonical position from label {field}")
        seen_indices.add(canonical)
        entries.append(
            {
                "logical_qubit_index": canonical,
                "qir_result_index": canonical,
                "provider_field": field,
                "provider_subindex": 0,
                "provider_result_position": provider_position,
                "canonical_position": canonical,
                "mapping_source": "helios_1e_deterministic_cases_and_qir_labels",
                "mapping_confidence": "verified",
            }
        )
    if seen_indices != set(range(98)):
        raise ValueError("Provider mapping does not uniquely resolve all 98 positions")
    return {
        "provider_result_order_verified": True,
        "emulator_mapping_validation_passed": True,
        "resolved_positions": 98,
        "unresolved_positions": 0,
        "provider_layout": list(layout),
        "entries": sorted(entries, key=lambda entry: entry["canonical_position"]),
        "case_reports": case_reports,
        "raw_value_count": sum(len(parsed.values) for parsed in parsed_cases.values()),
        "parser_values": {
            name: [asdict(value) for value in parsed.values]
            for name, parsed in parsed_cases.items()
        },
    }
