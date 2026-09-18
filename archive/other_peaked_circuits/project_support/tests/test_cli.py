import shutil
from pathlib import Path

from typer.testing import CliRunner

from p12_recovery.cli import app

runner = CliRunner()


def isolated_project(source_root: Path, destination: Path) -> Path:
    project = destination / "project"
    project.mkdir()
    shutil.copy2(source_root / "pyproject.toml", project / "pyproject.toml")
    shutil.copytree(source_root / "circuits/fixtures", project / "circuits/fixtures")
    return project


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Hardware-safe" in result.stdout


def test_offline_doctor(root: Path, monkeypatch: object, tmp_path: Path) -> None:
    project = isolated_project(root, tmp_path)
    monkeypatch.chdir(project)  # type: ignore[attr-defined]
    result = runner.invoke(app, ["doctor"], env={"P12_ENABLE_HARDWARE": "0"})
    assert result.exit_code == 0
    assert "NOT_READY" in result.stdout
    assert "Ready for hardware submission: False" in result.stdout


def test_inspect_fixture_and_invalid_config(
    root: Path, monkeypatch: object, tmp_path: Path
) -> None:
    project = isolated_project(root, tmp_path)
    monkeypatch.chdir(project)  # type: ignore[attr-defined]
    result = runner.invoke(
        app, ["inspect", "--source", "circuits/fixtures/bell.qasm", "--no-figures"]
    )
    assert result.exit_code == 0
    bad = tmp_path / "bad.yaml"
    bad.write_text("[]")
    result = runner.invoke(app, ["synthetic", "--config", str(bad), "--smoke"])
    assert result.exit_code != 0


def test_synthetic_smoke(root: Path, monkeypatch: object, tmp_path: Path) -> None:
    project = isolated_project(root, tmp_path)
    monkeypatch.chdir(project)  # type: ignore[attr-defined]
    config = project / "synthetic.yaml"
    config.write_text("""schema_version: '1.0'
number_of_qubits: 98
seed: 4
targets: {mode: random, explicit_target: null}
shot_counts: [10]
bootstrap_replicates: 2
models:
  independent: {error_rates: [0.03]}
  asymmetric: {p_1_to_0: 0.06, p_0_to_1: 0.03}
  mixture: {target_weight: 0.7, secondary_weight: 0.2, uniform_weight: 0.1}
""")
    result = runner.invoke(app, ["synthetic", "--config", str(config), "--smoke"])
    assert result.exit_code == 0, result.stdout
