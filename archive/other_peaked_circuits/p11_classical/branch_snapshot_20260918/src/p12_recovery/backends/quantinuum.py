from __future__ import annotations

import importlib
import importlib.metadata
import inspect
import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from p12_recovery.models import (
    AvailableDevicesReport,
    BackendDescriptor,
    CompilationConfig,
    CostEstimate,
    ValidationResult,
)


class SDKCompatibilityError(RuntimeError):
    """Raised rather than silently ignoring a required SDK option."""


@dataclass(frozen=True)
class CompiledCircuitArtifact:
    circuit: Any
    initial_map: dict[str, str]
    final_map: dict[str, str]
    effective_options: dict[str, Any]


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def quantinuum_available() -> bool:
    return _version("pytket-quantinuum") is not None


def qnexus_available() -> bool:
    return _version("qnexus") is not None


def credentials_detected() -> bool:
    names = (
        "QNUX_TOKEN",
        "QUANTINUUM_API_TOKEN",
        "HQS_API_TOKEN",
        "NEXUS_MANAGED_TOKENS",
        "AZURE_QUANTUM_CONNECTION_STRING",
    )
    return any(bool(os.environ.get(name)) for name in names)


def sanitize_diagnostic(exc: BaseException) -> str:
    message = re.sub(r"[\w.+-]+@[\w.-]+", "<redacted-email>", str(exc))
    message = re.sub(r"(?i)bearer\s+[a-z0-9._~-]+", "Bearer <redacted>", message)
    message = re.sub(
        r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b",
        "<redacted-jwt>",
        message,
    )
    message = re.sub(
        r"(?i)(token|secret|password|credential|api[_ -]?key)\s*[:=]\s*\S+",
        r"\1=<redacted>",
        message,
    )
    return f"{type(exc).__name__}: {message[:500]}"


def _safe_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _safe_metadata(item)
            for key, item in value.items()
            if not re.search(
                r"(?i)token|secret|password|credential|api.?key|email|user|owner|auth|session",
                str(key),
            )
        }
    if isinstance(value, (list, tuple, set)):
        return [_safe_metadata(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"[\w.+-]+@[\w.-]+", "<redacted-email>", value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


def _metadata_target_type(misc: dict[str, Any], device_name: str | None) -> tuple[str, str]:
    for key in ("system_type", "systemType", "device_type", "deviceType", "type"):
        value = misc.get(key)
        if value:
            return str(value), f"BackendInfo.misc.{key}"
    lowered = (device_name or "").lower()
    if "syntax" in lowered or "checker" in lowered or lowered.endswith("sc"):
        return "syntax_checker", "device_name_fallback_low_confidence"
    if "emulator" in lowered or "simulator" in lowered or lowered.endswith("e"):
        return "emulator", "device_name_fallback_low_confidence"
    return "unknown", "metadata_unavailable"


def descriptor_from_backend_info(
    info: Any, *, metadata_source: str = "live_api", access_status: str = "accessible"
) -> BackendDescriptor:
    misc = _safe_metadata(dict(getattr(info, "misc", {}) or {}))
    architecture = getattr(info, "architecture", None)
    nodes = list(getattr(architecture, "nodes", []) or []) if architecture is not None else []
    capacity = len(nodes) or misc.get("n_qubits") or misc.get("nQubits")
    capacity = int(capacity) if capacity is not None else None
    device_name = getattr(info, "device_name", None)
    target_type, type_source = _metadata_target_type(misc, device_name)
    gates = sorted(
        getattr(op, "name", str(op)) for op in (getattr(info, "gate_set", set()) or set())
    )
    has_98 = capacity is not None and capacity >= 98
    return BackendDescriptor(
        provider="quantinuum",
        provider_api="legacy_pytket_quantinuum",
        device_name=device_name,
        target_type=target_type,
        target_type_source=type_source,
        qubit_capacity=capacity,
        gate_set=gates,
        classical_register_limit=getattr(info, "n_cl_reg", None),
        backend_version=str(getattr(info, "version", "")) or None,
        provider_metadata=misc,
        access_status=access_status,
        metadata_source=metadata_source,  # type: ignore[arg-type]
        has_at_least_98_qubits=has_98,
        p12_compatible=has_98,
        sdk_versions={
            "pytket": _version("pytket"),
            "pytket-quantinuum": _version("pytket-quantinuum"),
            "qnexus": _version("qnexus"),
        },
        credentials_detected=credentials_detected(),
        available=True,
    )


def discover_quantinuum_devices() -> list[BackendDescriptor]:
    if not quantinuum_available():
        raise RuntimeError("pytket-quantinuum is not installed")
    module = importlib.import_module("pytket.extensions.quantinuum")
    backend_class = module.QuantinuumBackend
    # pytket-quantinuum >=0.56 no longer submits to Quantinuum systems. Its
    # device list is useful metadata, but it cannot establish account access.
    access = "legacy_metadata_accessible_account_access_unverified"
    return [
        descriptor_from_backend_info(info, access_status=access)
        for info in backend_class.available_devices()
    ]


class NexusAuthenticationRequired(RuntimeError):
    """Raised when discovery needs an existing non-interactive Nexus session."""


def descriptor_from_nexus_device(device: Any) -> BackendDescriptor:
    """Convert qnexus device metadata without retaining account identifiers."""
    info = device.stored_backend_info
    raw_misc = dict(getattr(info, "misc", {}) or {})
    misc = _safe_metadata(raw_misc)
    stored_device = getattr(info, "device", None)
    nodes = list(getattr(stored_device, "nodes", []) or []) if stored_device else []
    n_nodes = getattr(stored_device, "n_nodes", None) if stored_device else None
    capacity = int(n_nodes or len(nodes)) if n_nodes or nodes else None
    device_name = getattr(device, "device_name", None) or getattr(info, "device_name", None)
    exact_helios_types = {
        "Helios-1SC": "syntax_checker",
        "Helios-1E": "emulator",
        "Helios-1": "hardware",
    }
    if device_name in exact_helios_types:
        target_type = exact_helios_types[device_name]
        type_source = "authenticated_nexus_system_name"
    else:
        target_type, type_source = _metadata_target_type(raw_misc, device_name)
    if target_type == "unknown":
        classifier = " ".join(
            str(value)
            for value in (
                device_name,
                getattr(device, "backend_name", None),
                getattr(info, "name", None),
            )
            if value
        ).lower()
        if "checker" in classifier or "syntax" in classifier:
            target_type, type_source = "syntax_checker", "nexus_name_fallback_low_confidence"
        elif "emulator" in classifier or "selene" in classifier or "-1e" in classifier:
            target_type, type_source = "emulator", "nexus_name_fallback_low_confidence"
        elif "helios" in classifier or re.search(r"\bh[12]-", classifier):
            target_type, type_source = "hardware", "nexus_name_fallback_low_confidence"
    has_98 = capacity is not None and capacity >= 98
    metadata = {
        "api_surface": "nexus",
        "backend_name": getattr(device, "backend_name", None),
        "nexus_hosted": bool(getattr(device, "nexus_hosted", False)),
        "stored_backend_name": getattr(info, "name", None),
        "supports_fast_feedforward": getattr(info, "supports_fast_feedforward", None),
        "supports_reset": getattr(info, "supports_reset", None),
        "supports_midcircuit_measurement": getattr(
            info, "supports_midcircuit_measurement", None
        ),
        "misc": misc,
    }
    return BackendDescriptor(
        provider="quantinuum",
        provider_api="nexus",
        device_name=device_name,
        target_type=target_type,
        target_type_source=type_source,
        qubit_capacity=capacity,
        gate_set=sorted(str(gate) for gate in (getattr(info, "gate_set", []) or [])),
        classical_register_limit=getattr(info, "n_cl_reg", None),
        backend_version=str(getattr(info, "version", "")) or None,
        provider_metadata=_safe_metadata(metadata),
        access_status="listed_for_authenticated_nexus_account",
        metadata_source="live_api",
        has_at_least_98_qubits=has_98,
        p12_compatible=has_98,
        sdk_versions={
            "pytket": _version("pytket"),
            "pytket-quantinuum": _version("pytket-quantinuum"),
            "qnexus": _version("qnexus"),
        },
        credentials_detected=True,
        available=True,
        notes=[
            "Helios systems require qnexus.models.HeliosConfig(system_name=...), not "
            "the legacy QuantinuumConfig(device_name=...) submission path."
        ]
        if str(device_name).startswith("Helios")
        else [],
    )


def classify_nexus_device(device: Any) -> BackendDescriptor:
    """Public classification entry point used by discovery and regression tests."""
    return descriptor_from_nexus_device(device)


def discover_nexus_devices() -> list[BackendDescriptor]:
    """List Quantinuum targets visible to an already-authenticated Nexus session."""
    if not qnexus_available():
        raise RuntimeError("qnexus is not installed; install the quantum optional dependency")
    module = importlib.import_module("qnexus")
    if not bool(module.auth.is_logged_in()):
        raise NexusAuthenticationRequired(
            "No authenticated Nexus session is available. Run `qnx login` or "
            "`python -c \"import qnexus as qnx; qnx.login()\"` outside this repository; "
            "never paste credentials into project files or logs."
        )
    issuer = module.models.IssuerEnum.QUANTINUUM
    return [
        classify_nexus_device(device)
        for device in module.devices.get_all(issuers=[issuer])
    ]


def discover_quantinuum_report() -> AvailableDevicesReport:
    devices: list[BackendDescriptor] = []
    diagnostics: list[str] = []
    surfaces: dict[str, str] = {}
    authenticated = False
    try:
        nexus_devices = discover_nexus_devices()
        devices.extend(nexus_devices)
        surfaces["nexus"] = "success"
        authenticated = True
    except Exception as exc:
        surfaces["nexus"] = "unavailable"
        diagnostics.append(f"Nexus discovery: {sanitize_diagnostic(exc)}")
    try:
        legacy_devices = discover_quantinuum_devices()
        devices.extend(legacy_devices)
        surfaces["legacy_pytket_quantinuum"] = "success_access_unverified"
    except Exception as exc:
        surfaces["legacy_pytket_quantinuum"] = "unavailable"
        diagnostics.append(f"Legacy discovery: {sanitize_diagnostic(exc)}")
    successful_surfaces = sum(value.startswith("success") for value in surfaces.values())
    status: Literal["success", "partial", "failed"] = (
        "success" if successful_surfaces == len(surfaces) else "partial"
    )
    if successful_surfaces == 0:
        status = "failed"
    return AvailableDevicesReport(
        status=status,
        devices=devices,
        diagnostics=diagnostics,
        live_api_access=successful_surfaces > 0,
        authenticated_access=authenticated,
        discovery_surfaces=surfaces,
        package_versions={
            "pytket": _version("pytket"),
            "pytket-quantinuum": _version("pytket-quantinuum"),
            "qnexus": _version("qnexus"),
        },
    )


def build_compilation_config(options: dict[str, Any]) -> Any:
    module = importlib.import_module("pytket.extensions.quantinuum.backends.quantinuum")
    config_class = module.QuantinuumBackendCompilationConfig
    signature = inspect.signature(config_class)
    required = {
        "preserve_qubit_names": bool(options.get("preserve_qubit_names", True)),
        "allow_implicit_swaps": bool(options.get("allow_implicit_swaps", False)),
    }
    unsupported = sorted(set(required) - set(signature.parameters))
    if unsupported:
        raise SDKCompatibilityError(
            f"Installed pytket-quantinuum does not support required options: {unsupported}"
        )
    target_gate = options.get("target_2qb_gate")
    if target_gate is not None:
        if "target_2qb_gate" not in signature.parameters:
            raise SDKCompatibilityError("Installed SDK does not support target_2qb_gate")
        pytket = importlib.import_module("pytket.circuit")
        try:
            required["target_2qb_gate"] = getattr(pytket.OpType, str(target_gate))
        except AttributeError as exc:
            raise SDKCompatibilityError(f"Unknown target_2qb_gate: {target_gate}") from exc
    return config_class(**required)


class QuantinuumCompilationBackend:
    def __init__(
        self, device_name: str | None, *, descriptor: BackendDescriptor | None = None
    ) -> None:
        self.device_name = device_name
        self.live_descriptor = descriptor
        self._backend: Any | None = None

    def describe(self) -> BackendDescriptor:
        if self.live_descriptor is not None:
            return self.live_descriptor
        return BackendDescriptor(
            provider="quantinuum",
            provider_api="unselected",
            device_name=self.device_name,
            target_type="unknown",
            target_type_source="metadata_not_loaded",
            metadata_source="offline",
            access_status="not_tested",
            sdk_versions={
                "pytket": _version("pytket"),
                "pytket-quantinuum": _version("pytket-quantinuum"),
                "qnexus": _version("qnexus"),
            },
            credentials_detected=credentials_detected(),
            available=quantinuum_available(),
            notes=["Run `p12-recovery devices` to obtain live metadata"],
        )

    def _instance(self, config: CompilationConfig | None = None) -> Any:
        if not quantinuum_available():
            raise RuntimeError("pytket-quantinuum is not installed")
        if not self.device_name:
            raise RuntimeError("No exact discovered Quantinuum target configured")
        if self.live_descriptor and self.live_descriptor.provider_api == "nexus":
            raise RuntimeError(
                "This target was discovered through Nexus. Helios uses HeliosConfig(system_name=...) "
                "and the Nexus HUGR/QIR workflow; it must not be compiled as a legacy H-series "
                "QuantinuumBackend. Remote Nexus uploads/compile jobs are deliberately not started "
                "by this hardware-safe Milestone 2 command."
            )
        if self._backend is None:
            module = importlib.import_module("pytket.extensions.quantinuum")
            kwargs: dict[str, Any] = {"device_name": self.device_name}
            if config is not None:
                kwargs["compilation_config"] = build_compilation_config(config.compiler)
            self._backend = module.QuantinuumBackend(**kwargs)
        return self._backend

    def compile(self, circuit: Any, config: CompilationConfig) -> CompiledCircuitArtifact:
        backend = self._instance(config)
        predicates = importlib.import_module("pytket.predicates")
        unit = predicates.CompilationUnit(circuit)
        level = int(config.compiler.get("optimization_level", 1))
        timeout = int(config.compiler.get("timeout_seconds", 1800))
        backend.default_compilation_pass(optimisation_level=level, timeout=timeout).apply(unit)
        return CompiledCircuitArtifact(
            circuit=unit.circuit,
            initial_map={str(k): str(v) for k, v in unit.initial_map.items()},
            final_map={str(k): str(v) for k, v in unit.final_map.items()},
            effective_options={
                "optimization_level": level,
                "timeout_seconds": timeout,
                "preserve_qubit_names": bool(config.compiler.get("preserve_qubit_names", True)),
                "allow_implicit_swaps": bool(config.compiler.get("allow_implicit_swaps", False)),
                "target_2qb_gate": config.compiler.get("target_2qb_gate"),
            },
        )

    def validate(self, circuit: Any) -> ValidationResult:
        backend = self._instance()
        predicates: dict[str, bool | None] = {}
        diagnostics: list[str] = []
        try:
            for predicate in backend.required_predicates:
                name = type(predicate).__name__
                try:
                    predicates[name] = bool(predicate.verify(circuit))
                except Exception as exc:
                    predicates[name] = None
                    diagnostics.append(sanitize_diagnostic(exc))
            predicates["backend.valid_circuit"] = bool(backend.valid_circuit(circuit))
        except Exception as exc:
            diagnostics.append(sanitize_diagnostic(exc))
        return ValidationResult(
            passed=bool(predicates) and all(value is True for value in predicates.values()),
            predicates=predicates,
            diagnostics=diagnostics,
        )

    def estimate_cost(self, circuit: Any, shots: int) -> CostEstimate | None:
        del circuit, shots
        return None

    def submit(self, circuit: Any, shots: int) -> Any:
        del circuit, shots
        raise NotImplementedError("Milestone 2 has no paid hardware execution implementation.")
