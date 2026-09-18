from __future__ import annotations

from typing import Any

import pytest

from p12_recovery.emulator_guard import (
    HeliosEmulatorExecutionBlocked,
    assert_helios_emulator_execution_allowed,
)


def valid() -> dict[str, Any]:
    return {
        "execute_emulator": True,
        "environment": {"P12_ENABLE_HELIOS_EMULATOR": "1"},
        "target": "Helios-1E",
        "target_classification": "emulator",
        "authenticated_discovery": True,
        "discovered_targets": {"Helios-1E", "Helios-1SC", "Helios-1"},
        "mapping_syntax_checks_passed": True,
        "p12_syntax_check_passed": True,
        "cost_evidence_exists": True,
        "max_cost": 5.0,
        "expected_bitcode_hash": "frozen",
        "actual_bitcode_hash": "frozen",
        "mapping_validation_passed": True,
        "is_p12_pilot": False,
        "interactive_confirmed": True,
    }


def test_emulator_guard_allows_exact_authorized_target() -> None:
    assert_helios_emulator_execution_allowed(**valid())


@pytest.mark.parametrize(
    "override",
    [
        {"execute_emulator": False},
        {"environment": {}},
        {"target": "Helios-1", "target_classification": "hardware"},
        {"target": "Helios-1SC", "target_classification": "syntax_checker"},
        {"target": "H2-1E"},
        {"authenticated_discovery": False},
        {"discovered_targets": set()},
        {"mapping_syntax_checks_passed": False},
        {"cost_evidence_exists": False},
        {"max_cost": None},
        {"max_cost": 0.0},
        {"actual_bitcode_hash": "changed"},
        {"interactive_confirmed": False},
    ],
)
def test_emulator_guard_blocks_missing_condition(override: dict[str, Any]) -> None:
    values = valid() | override
    with pytest.raises(HeliosEmulatorExecutionBlocked):
        assert_helios_emulator_execution_allowed(**values)


def test_p12_guard_requires_syntax_and_mapping() -> None:
    values = valid() | {
        "is_p12_pilot": True,
        "p12_syntax_check_passed": False,
        "mapping_validation_passed": False,
    }
    with pytest.raises(HeliosEmulatorExecutionBlocked) as exc:
        assert_helios_emulator_execution_allowed(**values)
    assert "P12" in str(exc.value)
    assert "mapping" in str(exc.value)
