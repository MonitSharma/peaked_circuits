from pathlib import Path

from p12_recovery.public_audit import run_public_audit


def clean_fixture(root: Path) -> None:
    (root / "CITATION.cff").write_text(
        "repository-code: https://github.com/MonitSharma/p12-helios-recovery\n"
        "authors:\n  - family-names: Sharma\n    given-names: Monit\n"
    )
    (root / "LICENSE").write_text("Apache License")
    (root / ".gitignore").write_text("data/provider_raw/*\ndata/canonical/*\ndata/hardware/*\n")


def test_public_audit_passes_clean_fixture(tmp_path: Path) -> None:
    clean_fixture(tmp_path)
    assert run_public_audit(tmp_path).passed


def test_public_audit_detects_env_token_paths_and_wrong_url(tmp_path: Path) -> None:
    clean_fixture(tmp_path)
    (tmp_path / ".env").write_text("TOKEN=" + "github" + "_pat_1234567890123456789012345")
    local_path = "/" + "Users/example/private"
    (tmp_path / "report.json").write_text('{"path":"' + local_path + '"}')
    (tmp_path / "CITATION.cff").write_text("repository-code: https://wrong.example\n")
    report = run_public_audit(tmp_path)
    failures = {item.check for item in report.findings if not item.passed}
    assert {
        "no_dot_env",
        "no_token_values",
        "no_local_absolute_paths",
        "correct_repository_url",
    }.issubset(failures)


def test_public_audit_detects_nexus_cache_and_unsafe_qir(tmp_path: Path) -> None:
    clean_fixture(tmp_path)
    (tmp_path / ".qnx").mkdir()
    qir = tmp_path / "results/qir/unsafe.ll"
    qir.parent.mkdir(parents=True)
    qir.write_text("; token=" + "unsafe-value")
    report = run_public_audit(tmp_path)
    failures = {item.check for item in report.findings if not item.passed}
    assert {"no_local_nexus_auth_cache", "qir_artifacts_sanitized"}.issubset(failures)
