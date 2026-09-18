from types import SimpleNamespace

import pytest

import p12_recovery.backends.quantinuum as quantinuum
from p12_recovery.backends.quantinuum import (
    QuantinuumCompilationBackend,
    SDKCompatibilityError,
    build_compilation_config,
    classify_nexus_device,
    descriptor_from_backend_info,
    descriptor_from_nexus_device,
    discover_quantinuum_report,
)
from p12_recovery.models import BackendDescriptor


def test_metadata_driven_device_descriptor() -> None:
    gate_a = type("Gate", (), {"name": "ZZPhase"})()
    gate_b = type("Gate", (), {"name": "Rz"})()
    info = SimpleNamespace(
        device_name="opaque-device-name",
        version="2026.7",
        architecture=SimpleNamespace(nodes=list(range(100))),
        gate_set={gate_a, gate_b},
        n_cl_reg=4,
        misc={"system_type": "hardware", "region": "test", "api_token": "never-store"},
    )
    descriptor = descriptor_from_backend_info(info)
    assert descriptor.target_type == "hardware"
    assert descriptor.target_type_source == "BackendInfo.misc.system_type"
    assert descriptor.qubit_capacity == 100
    assert descriptor.has_at_least_98_qubits and descriptor.p12_compatible
    assert "api_token" not in descriptor.provider_metadata


def test_discovery_authentication_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> list[object]:
        raise RuntimeError("token=fixture-secret person@example.com")

    monkeypatch.setattr(quantinuum, "discover_quantinuum_devices", fail)
    monkeypatch.setattr(quantinuum, "discover_nexus_devices", fail)
    report = discover_quantinuum_report()
    assert report.status == "failed"
    rendered = report.model_dump_json()
    assert "fixture-secret" not in rendered
    assert "person@example.com" not in rendered


def test_nexus_helios_descriptor_uses_system_metadata() -> None:
    device = SimpleNamespace(
        backend_name="Helios",
        device_name="Helios-1",
        nexus_hosted=False,
        stored_backend_info=SimpleNamespace(
            name="HeliosBackend",
            device_name="Helios-1",
            version="2026.7",
            device=SimpleNamespace(n_nodes=98, nodes=[]),
            gate_set=["Rz", "ZZPhase", "Measure"],
            n_cl_reg=1,
            supports_fast_feedforward=True,
            supports_reset=True,
            supports_midcircuit_measurement=True,
            misc={
                "system_type": "hardware",
                "credential_name": "must-not-survive",
                "owner": "person@example.com",
            },
        ),
    )
    descriptor = descriptor_from_nexus_device(device)
    assert descriptor.provider_api == "nexus"
    assert descriptor.target_type == "hardware"
    assert descriptor.qubit_capacity == 98
    assert descriptor.p12_compatible
    assert descriptor.access_status == "listed_for_authenticated_nexus_account"
    assert "credential_name" not in descriptor.model_dump_json()
    assert "person@example.com" not in descriptor.model_dump_json()


def test_helios_cannot_fall_through_to_legacy_backend() -> None:
    descriptor = BackendDescriptor(
        provider="quantinuum",
        provider_api="nexus",
        device_name="Helios-1",
        qubit_capacity=98,
    )
    adapter = QuantinuumCompilationBackend("Helios-1", descriptor=descriptor)
    with pytest.raises(RuntimeError, match="HeliosConfig"):
        adapter._instance()


def test_nexus_helios_syntax_checker_suffix_is_classified() -> None:
    device = SimpleNamespace(
        backend_name="Helios",
        device_name="Helios-1SC",
        nexus_hosted=False,
        stored_backend_info=SimpleNamespace(
            name="HeliosBackend",
            device_name="Helios-1SC",
            version="2026.7",
            device=SimpleNamespace(n_nodes=98, nodes=[]),
            gate_set=[],
            n_cl_reg=None,
            supports_fast_feedforward=True,
            supports_reset=True,
            supports_midcircuit_measurement=True,
            misc={},
        ),
    )
    descriptor = descriptor_from_nexus_device(device)
    assert descriptor.target_type == "syntax_checker"
    assert descriptor.target_type_source == "authenticated_nexus_system_name"


def _nexus_device(name: str, system_type: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        backend_name="Helios",
        device_name=name,
        nexus_hosted=False,
        stored_backend_info=SimpleNamespace(
            name="HeliosBackend",
            device_name=name,
            version="2026.7",
            device=SimpleNamespace(n_nodes=98, nodes=[]),
            gate_set=[],
            n_cl_reg=None,
            supports_fast_feedforward=True,
            supports_reset=True,
            supports_midcircuit_measurement=True,
            misc={"system_type": system_type} if system_type else {},
        ),
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Helios-1SC", "syntax_checker"),
        ("Helios-1E", "emulator"),
        ("Helios-1", "hardware"),
    ],
)
def test_authenticated_helios_system_names_have_exact_types(name: str, expected: str) -> None:
    descriptor = classify_nexus_device(_nexus_device(name, system_type="emulator"))
    assert descriptor.device_name == name
    assert descriptor.target_type == expected
    if name == "Helios-1SC":
        assert descriptor.target_type != "emulator"


def test_nexus_metadata_precedes_fallback_for_opaque_name() -> None:
    descriptor = classify_nexus_device(_nexus_device("opaque-target", "syntax_checker"))
    assert descriptor.target_type == "syntax_checker"
    assert descriptor.target_type_source == "BackendInfo.misc.system_type"


def test_unknown_nexus_target_is_not_assumed_safe() -> None:
    device = _nexus_device("opaque-target")
    device.backend_name = "opaque-backend"
    device.stored_backend_info.name = "OpaqueBackend"
    descriptor = classify_nexus_device(device)
    assert descriptor.target_type == "unknown"


def test_partial_report_does_not_treat_legacy_metadata_as_authenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy = BackendDescriptor(provider="quantinuum", device_name="H2-1")
    monkeypatch.setattr(quantinuum, "discover_quantinuum_devices", lambda: [legacy])
    monkeypatch.setattr(
        quantinuum,
        "discover_nexus_devices",
        lambda: (_ for _ in ()).throw(RuntimeError("no Nexus session")),
    )
    report = discover_quantinuum_report()
    assert report.status == "partial"
    assert report.authenticated_access is False
    assert report.discovery_surfaces["nexus"] == "unavailable"


def test_required_compilation_options_are_effective() -> None:
    config = build_compilation_config({"preserve_qubit_names": True, "allow_implicit_swaps": False})
    assert config.preserve_qubit_names is True
    assert config.allow_implicit_swaps is False


def test_unsupported_compilation_option_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class IncompatibleConfig:
        def __init__(self, preserve_qubit_names: bool = False) -> None:
            self.preserve_qubit_names = preserve_qubit_names

    fake = SimpleNamespace(QuantinuumBackendCompilationConfig=IncompatibleConfig)
    monkeypatch.setattr(quantinuum.importlib, "import_module", lambda _: fake)
    with pytest.raises(SDKCompatibilityError, match="allow_implicit_swaps"):
        build_compilation_config({"preserve_qubit_names": True, "allow_implicit_swaps": False})
