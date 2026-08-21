from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .config import load_yaml
from .hashing import hash_config
from .models import CompilationReport, MappingValidationReport, ProtocolFreezeRecord
from .reporting import git_state, write_json


class ProtocolFreezeBlocked(RuntimeError):
    pass


def _require(condition: bool, name: str, prerequisites: dict[str, bool]) -> None:
    prerequisites[name] = condition


def freeze_protocol(root: Path, config_path: Path) -> ProtocolFreezeRecord:
    commit, dirty = git_state(root)
    if not commit:
        raise ProtocolFreezeBlocked("Repository has no commit to freeze")
    if dirty:
        raise ProtocolFreezeBlocked(
            "Working tree is dirty; protocol freeze requires a clean commit"
        )
    config = load_yaml(config_path)
    compilation_path = root / "results/compilation/compilation_report.json"
    mapping_path = root / "results/compilation/measurement_mapping.json"
    mapping_validation_path = root / "results/mapping_validation/mapping_validation_report.json"
    cost_path = root / "results/cost/cost_estimate.json"
    qir_export = root / "results/qir/qir_export_report.json"
    qir_validation = root / "results/qir/qir_validation_report.json"
    qir_mapping = root / "results/qir/qir_output_mapping.json"
    provider_mapping = root / "results/nexus/emulator_mapping/provider_output_mapping.json"
    nexus_cost = root / "results/nexus/cost/p12_cost.json"
    prerequisites: dict[str, bool] = {}
    compilation: CompilationReport | None = None
    if compilation_path.is_file():
        compilation = CompilationReport.model_validate_json(compilation_path.read_text())
    mapping_report: MappingValidationReport | None = None
    if mapping_validation_path.is_file():
        mapping_report = MappingValidationReport.model_validate_json(
            mapping_validation_path.read_text()
        )
    _require(
        bool(config.get("circuit", {}).get("source_hash")), "source_hash_exists", prerequisites
    )
    qir_export_payload = json.loads(qir_export.read_text()) if qir_export.is_file() else {}
    qir_validation_payload = json.loads(qir_validation.read_text()) if qir_validation.is_file() else {}
    qir_mapping_payload = json.loads(qir_mapping.read_text()) if qir_mapping.is_file() else {}
    provider_mapping_payload = json.loads(provider_mapping.read_text()) if provider_mapping.is_file() else {}
    _require(bool((compilation and compilation.compiled and compilation.compiled.get("compiled_qasm_hash")) or qir_export_payload.get("qir_sha256")), "compiled_hash_exists", prerequisites)
    _require(
        bool((compilation and compilation.backend.device_name) or config.get("backend", {}).get("device_name")), "target_identified", prerequisites
    )
    _require(
        bool((compilation and compilation.validation and compilation.validation.passed) or qir_validation_payload.get("status") == "passed"),
        "target_validation_passed",
        prerequisites,
    )
    _require(mapping_path.is_file() or len(qir_mapping_payload.get("entries", [])) == 98, "measurement_mapping_exists", prerequisites)
    _require(
        bool((mapping_report and mapping_report.status == "passed") or provider_mapping_payload.get("provider_result_order_verified") is True),
        "mapping_validation_passed",
        prerequisites,
    )
    _require(
        (cost_path.is_file() and json.loads(cost_path.read_text()).get("status") == "supported") or (nexus_cost.is_file() and json.loads(nexus_cost.read_text()).get("status") == "supported"),
        "provider_cost_exists",
        prerequisites,
    )
    primary = config.get("primary_analysis", {})
    _require(
        bool(primary.get("method") and primary.get("tie_policy")),
        "primary_method_explicit",
        prerequisites,
    )
    _require(
        all(
            isinstance(config.get(name), int) and config[name] > 0
            for name in ("primary_shots", "pilot_shots", "smoke_test_shots")
        ),
        "shot_counts_explicit",
        prerequisites,
    )
    failed = [name for name, passed in prerequisites.items() if not passed]
    if failed:
        raise ProtocolFreezeBlocked("Protocol prerequisites are incomplete: " + ", ".join(failed))
    if compilation is None and not qir_export_payload.get("qir_sha256"):
        raise ProtocolFreezeBlocked("Compilation or QIR evidence became unavailable during freeze")
    frozen: dict[str, Any] = dict(config)
    frozen["status"] = "frozen"
    frozen["circuit"] = dict(frozen["circuit"])
    frozen["circuit"]["compiled_hash"] = (compilation.compiled["compiled_qasm_hash"] if compilation and compilation.compiled else qir_export_payload["qir_sha256"])
    frozen["backend"] = {
        "device_name": compilation.backend.device_name if compilation else config.get("backend", {}).get("device_name"),
        "target_type": compilation.backend.target_type if compilation else config.get("backend", {}).get("target_type", "hardware"),
    }
    protocol_hash = hash_config(frozen)
    frozen["protocol_hash"] = protocol_hash
    config_path.write_text(yaml.safe_dump(frozen, sort_keys=False))
    record = ProtocolFreezeRecord(
        status="frozen",
        protocol_hash=protocol_hash,
        configuration_path=config_path.relative_to(root).as_posix(),
        configuration=frozen,
        prerequisites=prerequisites,
        git_commit=commit,
        git_dirty=False,
    )
    protocol_output = root / "results/protocol/protocol_freeze.json"
    protocol_output.parent.mkdir(parents=True, exist_ok=True)
    protocol_output.write_text(record.model_dump_json(indent=2) + "\n")
    return record
