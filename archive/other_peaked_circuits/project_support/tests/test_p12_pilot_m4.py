from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from p12_recovery.nexus_emulator import execute_p12_pilot


class FakeModels:
    simulator_kwargs: ClassVar[dict[str, Any]] = {}

    @classmethod
    def MatrixProductStateSimulator(cls, **kwargs: Any) -> SimpleNamespace:
        cls.simulator_kwargs = kwargs
        return SimpleNamespace(type="MatrixProductStateSimulator", **kwargs)

    @staticmethod
    def NoErrorModel() -> SimpleNamespace:
        return SimpleNamespace(type="NoErrorModel")

    @staticmethod
    def HeliosEmulatorConfig(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    @staticmethod
    def HeliosConfig(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)


class FakeJobs:
    @staticmethod
    def wait_for(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("CuTensornet Error #15: NOT_SUPPORTED; rzz failed")

    @staticmethod
    def status(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            status="ERROR",
            cost=0.0,
            error_detail="Selene error: Failed to apply RZZ gate",
        )

    @staticmethod
    def results(*_args: Any, **_kwargs: Any) -> list[Any]:
        raise AssertionError("results must not be requested after wait failure")


def pilot_root(tmp_path: Path) -> Path:
    source = Path("results/qir/qir_export_report.json")
    report = tmp_path / source
    report.parent.mkdir(parents=True)
    shutil.copyfile(source, report)
    bitcode = Path("results/qir/p12.bc")
    shutil.copyfile(bitcode, tmp_path / bitcode)
    return tmp_path


def test_pilot_uses_bounded_mps_and_preserves_job_error(tmp_path: Path) -> None:
    root = pilot_root(tmp_path)
    submitted: dict[str, Any] = {}

    def start_execute_job(**kwargs: Any) -> SimpleNamespace:
        submitted.update(kwargs)
        return SimpleNamespace(id="failed-rzz-job")

    client = SimpleNamespace(
        projects=SimpleNamespace(get_or_create=lambda **_: SimpleNamespace(id="project")),
        qir=SimpleNamespace(upload=lambda **_: SimpleNamespace(id="qir")),
        models=FakeModels,
        start_execute_job=start_execute_job,
        jobs=FakeJobs,
    )
    report = execute_p12_pilot(
        root,
        target="Helios-1E",
        shots=1,
        max_cost=13.0,
        client_module=client,
    )

    assert report.status == "failed"
    assert report.job_ref == "failed-rzz-job"
    assert report.final_status == "ERROR"
    assert report.reported_cost_hqcs == 0.0
    assert "RZZ" in report.diagnostics[0]
    assert FakeModels.simulator_kwargs == {
        "backend": "auto",
        "chi": 128,
        "zero_threshold": 0.01,
    }
    assert submitted["max_cost"] == [13.0]
    assert submitted["n_qubits"] == [98]
    failure_path = root / "results/nexus/p12_emulator/failed-rzz-job/pilot_report.json"
    assert failure_path.is_file()
    assert (failure_path.parent / "diagnostics.txt").is_file()
    assert (root / "data/provider_raw/p12_emulator/failed-rzz-job/job.json").is_file()


@pytest.mark.parametrize("shots", [0, 21])
def test_pilot_rejects_shots_outside_milestone_limit(tmp_path: Path, shots: int) -> None:
    with pytest.raises(ValueError, match=r"1\.\.20"):
        execute_p12_pilot(
            tmp_path,
            target="Helios-1E",
            shots=shots,
            max_cost=1.0,
            client_module=object(),
        )
