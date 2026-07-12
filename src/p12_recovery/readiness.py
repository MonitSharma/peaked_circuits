from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from .bit_ordering import raw_bitstring_to_canonical
from .hashing import read_sha256sums, sha256_file
from .models import HardwareReadinessReport
from .qasm_io import load_qasm
from .reporting import package_versions, write_json


def _fixture_checks(root: Path) -> bool:
    fixture = load_qasm(root / "circuits/fixtures/small_random.qasm")
    if fixture.sdk_circuit is None:
        return False
    state = fixture.sdk_circuit.get_statevector()
    normalized = bool(np.isclose(np.vdot(state, state), 1.0))
    mapped = raw_bitstring_to_canonical(
        "00001",
        logical_to_classical={i: i for i in range(5)},
        sdk_string_order="msb_left",
        register_layout=[{"name": "c", "classical_indices": list(range(5))}],
    )
    return normalized and mapped == "10000"


def build_readiness(root: Path) -> HardwareReadinessReport:
    qasm = root / "circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm"
    sums = qasm.parent / "SHA256SUMS"
    source_frozen = False
    if qasm.is_file() and sums.is_file():
        source_frozen = read_sha256sums(sums).get(qasm.name) == sha256_file(qasm)
    compilation_path = root / "results/compilation/compilation_report.json"
    compilation: dict[str, object] = {}
    if compilation_path.is_file():
        compilation = json.loads(compilation_path.read_text())
    backend = compilation.get("backend")
    validation = compilation.get("validation")
    checks: dict[str, bool | None] = {
        "source_hash_frozen": source_frozen,
        "compiler_version_frozen": bool(compilation.get("package_versions")),
        "backend_identified": bool(backend.get("device_name"))
        if isinstance(backend, dict)
        else False,
        "target_validity_passed": bool(validation.get("passed"))
        if isinstance(validation, dict)
        else False,
        "measurement_mapping_verified": (
            root / "results/compilation/measurement_mapping.json"
        ).is_file(),
        "synthetic_tests_passed": (root / "results/synthetic/synthetic_report.json").is_file(),
        "fixture_semantic_tests_passed": _fixture_checks(root),
        "cost_estimate_obtained": False,
        "shot_protocol_frozen": False,
        "recovery_method_frozen": False,
        "tracker_protocol_confirmed": False,
        "repository_commit_tagged": False,
        "hardware_guard_enabled": os.environ.get("P12_ENABLE_HARDWARE") == "1",
    }
    blockers = [name.replace("_", " ") for name, value in checks.items() if value is not True]
    report = HardwareReadinessReport(
        ready=False,
        checks=checks,
        blockers=blockers,
        package_versions=package_versions(),
        input_hashes={str(qasm): sha256_file(qasm)} if qasm.is_file() else {},
    )
    write_json(root / "results/hardware_readiness_report.json", report)
    markdown = "# Hardware readiness\n\n**NOT READY — Milestone 1 never enables submission.**\n\n"
    markdown += "\n".join(
        f"- [{'x' if value is True else ' '}] {name.replace('_', ' ')}"
        for name, value in checks.items()
    )
    markdown += "\n\nNo hardware execution was attempted and no paid resources were consumed.\n"
    (root / "docs/hardware_readiness.md").write_text(markdown)
    return report
