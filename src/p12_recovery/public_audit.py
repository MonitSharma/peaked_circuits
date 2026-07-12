from __future__ import annotations

import json
import re
from pathlib import Path

from .models import PublicAuditFinding, PublicAuditReport
from .reporting import package_versions, write_json

TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".cff",
    ".txt",
    ".csv",
    ".log",
    ".ll",
    ".bc",
    "",
}
EXCLUDED_PARTS = {".git", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__"}


def _text_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not EXCLUDED_PARTS.intersection(path.parts)
        and path.name not in {"public_audit.json", "public_audit.md", ".coverage"}
        and path.suffix.lower() in TEXT_SUFFIXES
    ]


def run_public_audit(root: Path) -> PublicAuditReport:
    files = _text_files(root)
    env_files = [path for path in files if path.name == ".env"]
    credential_files = [
        path
        for path in files
        if re.search(r"(?i)(credential|secret|token|api[_-]?key).*(json|txt|yaml|yml)$", path.name)
    ]
    token_paths: list[Path] = []
    absolute_paths: list[Path] = []
    hidden_target_paths: list[Path] = []
    qir_safety_failures: list[Path] = []
    nexus_result_safety_failures: list[Path] = []
    nexus_cache_paths = [
        path
        for name in (".qnx", ".qnexus", "nexus_auth", "nexus_tokens")
        if (path := root / name).exists()
    ]
    for path in files:
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if re.search(
            r"(?:gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})", text
        ):
            token_paths.append(path)
        local_prefixes = ("/" + "Users/", "/" + "home/")
        if any(prefix in text for prefix in local_prefixes):
            absolute_paths.append(path)
        if re.search(r'(?i)"(?:hidden_)?target_bitstring"\s*:\s*"[01]{98}"', text):
            hidden_target_paths.append(path)
        unsafe = bool(
            re.search(
                r"(?i)(?:bearer\s+[a-z0-9._~-]+|(?:token|secret|password|api[_ -]?key)\s*[:=]\s*\S+)",
                text,
            )
            or any(prefix in text for prefix in local_prefixes)
        )
        if path.suffix.lower() in {".ll", ".bc"} and unsafe:
            qir_safety_failures.append(path)
        if "results" in path.parts and "nexus" in path.parts and unsafe:
            nexus_result_safety_failures.append(path)
    citation = (root / "CITATION.cff").read_text() if (root / "CITATION.cff").is_file() else ""
    license_text = (root / "LICENSE").read_text() if (root / "LICENSE").is_file() else ""
    report_commit_failures: list[Path] = []
    report_hash_failures: list[Path] = []
    for path in (root / "results").rglob("*.json") if (root / "results").exists() else []:
        if path.name in {"public_audit.json"}:
            continue
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "created_at" in payload and not payload.get("git_commit"):
            report_commit_failures.append(path)
        if isinstance(payload, dict) and "created_at" in payload and "input_hashes" not in payload:
            report_hash_failures.append(path)
    raw_private = (
        list((root / "data/provider_raw").glob("*.json"))
        if (root / "data/provider_raw").exists()
        else []
    )
    findings = [
        PublicAuditFinding(
            check="no_dot_env",
            passed=not env_files,
            details="No committed .env files",
            paths=_relative(root, env_files),
        ),
        PublicAuditFinding(
            check="no_credential_files",
            passed=not credential_files,
            details="No credential-like files",
            paths=_relative(root, credential_files),
        ),
        PublicAuditFinding(
            check="no_token_values",
            passed=not token_paths,
            details="No token-like values",
            paths=_relative(root, token_paths),
        ),
        PublicAuditFinding(
            check="no_local_absolute_paths",
            passed=not absolute_paths,
            details="No local home-directory paths",
            paths=_relative(root, absolute_paths),
        ),
        PublicAuditFinding(
            check="no_hidden_target",
            passed=not hidden_target_paths,
            details="No 98-bit hidden target field",
            paths=_relative(root, hidden_target_paths),
        ),
        PublicAuditFinding(
            check="correct_repository_url",
            passed="https://github.com/MonitSharma/p12-helios-recovery" in citation,
            details="CITATION.cff repository URL",
        ),
        PublicAuditFinding(
            check="correct_author",
            passed="family-names: Sharma" in citation and "given-names: Monit" in citation,
            details="Monit Sharma software authorship metadata",
        ),
        PublicAuditFinding(
            check="license_present",
            passed="Apache License" in license_text,
            details="Apache-2.0 license present",
        ),
        PublicAuditFinding(
            check="reports_record_commit",
            passed=not report_commit_failures,
            details="ReportBase JSON artifacts record a Git commit",
            paths=_relative(root, report_commit_failures),
        ),
        PublicAuditFinding(
            check="reports_have_hash_fields",
            passed=not report_hash_failures,
            details="ReportBase JSON artifacts include input hash provenance",
            paths=_relative(root, report_hash_failures),
        ),
        PublicAuditFinding(
            check="no_raw_private_provider_metadata",
            passed=not raw_private,
            details="Provider raw results are not part of a public release",
            paths=_relative(root, raw_private),
        ),
        PublicAuditFinding(
            check="generated_data_ignored",
            passed=_gitignore_ok(root),
            details="Provider/canonical/hardware generated data are ignored",
        ),
        PublicAuditFinding(
            check="no_local_nexus_auth_cache",
            passed=not nexus_cache_paths,
            details="No Nexus token, browser-login, or local authentication cache is in the repository",
            paths=_relative(root, nexus_cache_paths),
        ),
        PublicAuditFinding(
            check="qir_artifacts_sanitized",
            passed=not qir_safety_failures,
            details="QIR text and bitcode contain no local paths or credential-like values",
            paths=_relative(root, qir_safety_failures),
        ),
        PublicAuditFinding(
            check="nexus_reports_sanitized",
            passed=not nexus_result_safety_failures,
            details="Nexus syntax-check reports contain sanitized references and diagnostics",
            paths=_relative(root, nexus_result_safety_failures),
        ),
    ]
    report = PublicAuditReport(
        passed=all(finding.passed for finding in findings),
        findings=findings,
        scanned_files=len(files),
        package_versions=package_versions(),
    )
    write_json(root / "results/public_audit.json", report)
    lines = "\n".join(
        f"- [{'x' if finding.passed else ' '}] {finding.check}: {finding.details}"
        for finding in findings
    )
    (root / "results/public_audit.md").write_text(
        f"# Public release audit\n\nPassed: **{report.passed}**\n\n{lines}\n"
    )
    return report


def _relative(root: Path, paths: list[Path]) -> list[str]:
    return [path.relative_to(root).as_posix() for path in paths]


def _gitignore_ok(root: Path) -> bool:
    path = root / ".gitignore"
    if not path.is_file():
        return False
    text = path.read_text()
    return all(
        value in text for value in ("data/provider_raw/*", "data/canonical/*", "data/hardware/*")
    )
