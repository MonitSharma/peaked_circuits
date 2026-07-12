from __future__ import annotations

from collections.abc import Mapping

from .constants import HARDWARE_CONFIRMATION


class HardwareSubmissionBlocked(PermissionError):
    pass


def assert_hardware_submission_allowed(
    *,
    execute_hardware: bool,
    environment: Mapping[str, str],
    readiness_passed: bool,
    device_is_physical: bool,
    backend_mode: str,
    interactive_confirmed: bool,
) -> None:
    reasons: list[str] = []
    if not execute_hardware:
        reasons.append("CLI flag --execute-hardware is absent")
    if environment.get("P12_ENABLE_HARDWARE") != "1":
        reasons.append("P12_ENABLE_HARDWARE must equal 1")
    if environment.get("P12_CONFIRM_PAID_EXECUTION") != HARDWARE_CONFIRMATION:
        reasons.append("P12_CONFIRM_PAID_EXECUTION does not contain the required phrase")
    if not readiness_passed:
        reasons.append("readiness validation has not passed")
    if device_is_physical and backend_mode == "compile_only":
        reasons.append("physical target is configured in compile-only mode")
    if not interactive_confirmed:
        reasons.append("interactive confirmation has not been completed")
    # Even a fully armed call remains unavailable in this milestone.
    reasons.append("Milestone 1 has no functioning hardware submission command")
    raise HardwareSubmissionBlocked("Hardware submission blocked: " + "; ".join(reasons))
