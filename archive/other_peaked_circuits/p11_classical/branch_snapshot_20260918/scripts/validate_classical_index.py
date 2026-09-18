#!/usr/bin/env python3
"""Validate the curated classical research index without importing project code."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "results/classical_index.json"
STATUSES = {"SOLVED_CLASSICAL", "VERIFIED_CONTROL", "UNRESOLVED", "METHOD_EXHAUSTED", "DIAGNOSTIC_ONLY"}
REQUIRED = {"problem", "status", "qubits", "two_qubit_gate_count", "method", "validation", "canonical_report", "artifact_manifest", "source_qasm", "source_sha256", "commit"}


def validate(path: Path = INDEX) -> list[str]:
    data = json.loads(path.read_text())
    errors: list[str] = []
    if data.get("schema") != "classical-research-index-v1":
        errors.append("unexpected schema")
    records = data.get("records")
    if not isinstance(records, list) or not records:
        return ["records must be a non-empty list"]
    seen: set[str] = set()
    for record in records:
        missing = REQUIRED - record.keys()
        if missing:
            errors.append(f"{record.get('problem', '?')}: missing {sorted(missing)}")
        problem = record.get("problem")
        if problem in seen:
            errors.append(f"duplicate problem: {problem}")
        seen.add(problem)
        if record.get("status") not in STATUSES:
            errors.append(f"{problem}: invalid status")
        if not isinstance(record.get("qubits"), int) or record["qubits"] <= 0:
            errors.append(f"{problem}: invalid qubit count")
        for field in ("canonical_report", "artifact_manifest"):
            target = ROOT / record.get(field, "")
            if not target.exists():
                errors.append(f"{problem}: missing {field} {record.get(field)}")
        source = record.get("source_qasm", "")
        if not source.startswith("not archived") and not (ROOT / source).exists():
            errors.append(f"{problem}: missing source_qasm {source}")
        digest = record.get("source_sha256", "")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            errors.append(f"{problem}: invalid source_sha256")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("\n".join(errors))
        return 1
    print(f"validated {INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
