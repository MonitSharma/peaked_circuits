"""Explicit logical q0-first <-> portal conversion for the peak campaign."""

from __future__ import annotations


def _validate(bits: str, permutation: list[int]) -> None:
    if set(bits) - {"0", "1"}:
        raise ValueError("bitstrings must contain only 0 and 1")
    if sorted(permutation) != list(range(len(bits))):
        raise ValueError("measurement permutation must be a permutation of bit positions")


def logical_q0_first_to_portal(bits: str, measurement_permutation: list[int] | None = None) -> str:
    """Return portal positions; permutation[i] identifies the logical bit at portal i."""
    permutation = measurement_permutation or list(range(len(bits)))
    _validate(bits, permutation)
    return "".join(bits[logical] for logical in permutation)


def portal_to_logical_q0_first(portal: str, measurement_permutation: list[int] | None = None) -> str:
    permutation = measurement_permutation or list(range(len(portal)))
    _validate(portal, permutation)
    logical = ["?"] * len(portal)
    for portal_position, logical_position in enumerate(permutation):
        logical[logical_position] = portal[portal_position]
    return "".join(logical)


def validate_p9_control(logical: str, portal: str, measurement_permutation: list[int]) -> dict[str, object]:
    converted = logical_q0_first_to_portal(logical, measurement_permutation)
    recovered = portal_to_logical_q0_first(portal, measurement_permutation)
    return {
        "status": "PASS" if converted == portal and recovered == logical else "FAIL",
        "measurement_permutation": measurement_permutation,
        "logical_q0_first": logical,
        "portal_observed": portal,
        "converted_portal": converted,
        "round_trip_logical": recovered,
        "answer_blind_for_target_problems": True,
        "p9_positive_control_exception": True,
    }
