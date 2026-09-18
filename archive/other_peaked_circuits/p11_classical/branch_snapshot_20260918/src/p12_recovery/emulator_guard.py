from __future__ import annotations

from collections.abc import Mapping, Set


class HeliosEmulatorExecutionBlocked(PermissionError):
    pass


def assert_helios_emulator_execution_allowed(
    *,
    execute_emulator: bool,
    environment: Mapping[str, str],
    target: str,
    target_classification: str,
    authenticated_discovery: bool,
    discovered_targets: Set[str],
    mapping_syntax_checks_passed: bool,
    p12_syntax_check_passed: bool,
    cost_evidence_exists: bool,
    max_cost: float | None,
    expected_bitcode_hash: str,
    actual_bitcode_hash: str,
    mapping_validation_passed: bool,
    is_p12_pilot: bool,
    interactive_confirmed: bool,
) -> None:
    """Enforce the paid-emulator boundary; physical targets can never pass."""
    reasons: list[str] = []
    if not execute_emulator:
        reasons.append("CLI flag --execute-emulator is absent")
    if environment.get("P12_ENABLE_HELIOS_EMULATOR") != "1":
        reasons.append("P12_ENABLE_HELIOS_EMULATOR must equal 1")
    if target != "Helios-1E":
        reasons.append("target must be exactly Helios-1E")
    if target_classification != "emulator":
        reasons.append("target is not classified as emulator")
    if not authenticated_discovery:
        reasons.append("authenticated Nexus discovery has not passed")
    if target not in discovered_targets:
        reasons.append("Helios-1E is not present in authenticated discovery")
    if not mapping_syntax_checks_passed:
        reasons.append("all six Helios-1SC mapping syntax checks must pass")
    if is_p12_pilot and not p12_syntax_check_passed:
        reasons.append("P12 Helios-1SC syntax check must pass before a P12 pilot")
    if not cost_evidence_exists:
        reasons.append("provider cost evidence is missing")
    if max_cost is None or max_cost <= 0:
        reasons.append("an explicit positive max_cost is required")
    if not expected_bitcode_hash or actual_bitcode_hash != expected_bitcode_hash:
        reasons.append("submitted artifact hash does not match frozen local bitcode")
    if is_p12_pilot and not mapping_validation_passed:
        reasons.append("P12 pilot is blocked until emulator mapping validation passes")
    if not interactive_confirmed:
        reasons.append("interactive emulator confirmation is incomplete")
    if reasons:
        raise HeliosEmulatorExecutionBlocked(
            "Helios emulator execution blocked: " + "; ".join(reasons)
        )
