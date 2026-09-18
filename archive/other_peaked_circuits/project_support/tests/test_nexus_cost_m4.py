from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from p12_recovery.hashing import sha256_file
from p12_recovery.nexus_cost import estimate_nexus_qir_costs


class FakeQIR:
    def __init__(self) -> None:
        self.uploaded: list[bytes] = []
        self.call: dict[str, object] = {}

    def upload(self, **kwargs: object) -> object:
        self.uploaded.append(kwargs["qir"])  # type: ignore[arg-type]
        return SimpleNamespace(id=f"qir-{len(self.uploaded)}")

    def cost_confidence(self, **kwargs: object) -> list[tuple[float, float]]:
        self.call = kwargs
        return [(5.25, 95.0), (5.5, 94.0)]


def test_cost_confidence_called_with_exact_program_and_shot_lists(tmp_path: Path) -> None:
    bitcode = tmp_path / "case.bc"
    bitcode.write_bytes(b"bitcode")
    qir = FakeQIR()
    client = SimpleNamespace(
        projects=SimpleNamespace(get_or_create=lambda **_: SimpleNamespace(id="project")),
        qir=qir,
    )
    report = estimate_nexus_qir_costs(
        tmp_path,
        target="Helios-1E",
        programs=[("case", bitcode, sha256_file(bitcode))],
        shots=[1, 3],
        client_module=client,
    )
    assert report.status == "supported"
    assert [item.shots for item in report.items] == [1, 3]
    assert [item.estimated_hqcs for item in report.items] == [5.25, 5.5]
    assert qir.call["n_shots"] == [1, 3]
    assert qir.call["system_name"] == "Helios-1"
    assert report.remote_costing_job_created
    assert not report.cost_job_reference_available_from_api


def test_unsupported_cost_api_is_structured_failure(tmp_path: Path) -> None:
    bitcode = tmp_path / "case.bc"
    bitcode.write_bytes(b"bitcode")
    client = SimpleNamespace(
        projects=SimpleNamespace(get_or_create=lambda **_: SimpleNamespace(id="project")),
        qir=SimpleNamespace(upload=lambda **_: object()),
    )
    report = estimate_nexus_qir_costs(
        tmp_path,
        target="Helios-1E",
        programs=[("case", bitcode, sha256_file(bitcode))],
        shots=[1],
        client_module=client,
    )
    assert report.status == "failed"
    assert report.items == []
    assert "cost_confidence" in report.diagnostics[0]
