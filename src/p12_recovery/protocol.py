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
    _require(
        bool(
            compilation and compilation.compiled and compilation.compiled.get("compiled_qasm_hash")
        ),
        "compiled_hash_exists",
        prerequisites,
    )
    _require(
        bool(compilation and compilation.backend.device_name), "target_identified", prerequisites
    )
    _require(
        bool(compilation and compilation.validation and compilation.validation.passed),
        "target_validation_passed",
        prerequisites,
    )
    _require(mapping_path.is_file(), "measurement_mapping_exists", prerequisites)
    _require(
        bool(mapping_report and mapping_report.status == "passed"),
        "mapping_validation_passed",
        prerequisites,
    )
    _require(
        cost_path.is_file() and json.loads(cost_path.read_text()).get("status") == "supported",
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
    if compilation is None or compilation.compiled is None:
        raise ProtocolFreezeBlocked("Compilation evidence became unavailable during freeze")
    frozen: dict[str, Any] = dict(config)
    frozen["status"] = "frozen"
    frozen["circuit"] = dict(frozen["circuit"])
    frozen["circuit"]["compiled_hash"] = compilation.compiled["compiled_qasm_hash"]
    frozen["backend"] = {
        "device_name": compilation.backend.device_name,
        "target_type": compilation.backend.target_type,
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
    write_json(root / "results/protocol/protocol_freeze.json", record)
    return record
