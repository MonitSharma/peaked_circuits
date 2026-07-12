from __future__ import annotations

from collections.abc import Mapping, Set


class NexusSyntaxCheckBlocked(PermissionError):
    pass


def assert_nexus_syntax_check_allowed(
    *,
    submit_syntax_check: bool,
    environment: Mapping[str, str],
    target: str,
    target_classification: str,
    authenticated_discovery: bool,
    discovered_targets: Set[str],
    qir_validation_passed: bool,
    logical_to_qir_mapping_verified: bool,
    expected_qir_hash: str,
    actual_qir_hash: str,
    validation_qir_hash: str | None,
    artifact_git_commit: str | None,
    current_git_commit: str | None,
    artifact_git_dirty: bool | None,
    current_git_dirty: bool | None,
    current_dirty_is_generated_artifacts_only: bool,
    mapping_syntax_checks_passed: bool,
    interactive_confirmed: bool,
) -> None:
    reasons: list[str] = []
    if not submit_syntax_check:
        reasons.append("CLI flag --submit-syntax-check is absent")
    if environment.get("P12_ENABLE_NEXUS_SYNTAX_CHECK") != "1":
        reasons.append("P12_ENABLE_NEXUS_SYNTAX_CHECK must equal 1")
    if target != "Helios-1SC":
        reasons.append("target must be exactly Helios-1SC")
    if target_classification != "syntax_checker":
        reasons.append("target is not classified as syntax_checker")
    if not authenticated_discovery:
        reasons.append("authenticated Nexus discovery has not passed")
    if target not in discovered_targets:
        reasons.append("Helios-1SC is not present in authenticated discovery")
    if not qir_validation_passed:
        reasons.append("strict local QIR validation has not passed")
    if not logical_to_qir_mapping_verified:
        reasons.append("logical-to-QIR mapping is incomplete")
    if not expected_qir_hash or actual_qir_hash != expected_qir_hash:
        reasons.append("QIR hash does not match the frozen export")
    if validation_qir_hash != actual_qir_hash:
        reasons.append("QIR hash does not match the validated artifact")
    import subprocess

    code_up_to_date = False
    critical_files = [
        "src/p12_recovery/qir_export.py",
        "src/p12_recovery/compilation.py",
        "src/p12_recovery/models.py",
        "src/p12_recovery/bit_ordering.py",
    ]
    if artifact_git_commit and current_git_commit:
        if artifact_git_commit == current_git_commit:
            code_up_to_date = True
        else:
            try:
                res = subprocess.run(
                    ["git", "merge-base", "--is-ancestor", artifact_git_commit, current_git_commit],
                    capture_output=True,
                )
                if res.returncode == 0:
                    diff_res = subprocess.run(
                        ["git", "diff", "--name-only", artifact_git_commit, current_git_commit, "--", *critical_files],
                        capture_output=True,
                        text=True,
                    )
                    if diff_res.returncode == 0 and not diff_res.stdout.strip():
                        code_up_to_date = True
            except Exception:
                pass

    if not code_up_to_date:
        if not artifact_git_commit or artifact_git_commit != current_git_commit:
            reasons.append("artifact Git commit does not match the current commit")
        allowed_generation_delta = (
            artifact_git_dirty is False
            and current_git_dirty is True
            and current_dirty_is_generated_artifacts_only
        )
        if artifact_git_dirty is None or (
            artifact_git_dirty != current_git_dirty and not allowed_generation_delta
        ):
            reasons.append("working-tree dirty state differs from artifact provenance")
    else:
        if artifact_git_commit != current_git_commit:
            has_critical_dirty = False
            try:
                dirty_res = subprocess.run(
                    ["git", "status", "--porcelain", "--", *critical_files],
                    capture_output=True,
                    text=True,
                )
                if dirty_res.returncode == 0 and dirty_res.stdout.strip():
                    has_critical_dirty = True
            except Exception:
                pass
            if has_critical_dirty:
                reasons.append("working tree has uncommitted code changes in critical files since artifact generation")
        else:
            allowed_generation_delta = (
                artifact_git_dirty is False
                and current_git_dirty is True
                and current_dirty_is_generated_artifacts_only
            )
            if artifact_git_dirty is None or (
                artifact_git_dirty != current_git_dirty and not allowed_generation_delta
            ):
                reasons.append("working-tree dirty state differs from artifact provenance")
    if not mapping_syntax_checks_passed:
        reasons.append("all six mapping QIR syntax checks must pass before P12")
    if not interactive_confirmed:
        reasons.append("interactive syntax-check confirmation is incomplete")
    if reasons:
        raise NexusSyntaxCheckBlocked("Nexus syntax check blocked: " + "; ".join(reasons))
