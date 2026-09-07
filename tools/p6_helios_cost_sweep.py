#!/usr/bin/env python3
"""Provider cost-confidence sweep for P6; never starts execution."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import qnexus as qnx


ROOT = Path(__file__).resolve().parents[1]
QIR = ROOT / "results/hardware/p6_helios_50shot_20260829/submitted.qir.bc"
QASM = Path("/Users/monitsharma/Downloads/P6_titan_pinnacle.qasm")
SHOTS = [1, 5, 10, 20, 50, 100, 150, 200, 300, 400]


def main() -> int:
    qir_hash = hashlib.sha256(QIR.read_bytes()).hexdigest()
    qasm_hash = hashlib.sha256(QASM.read_bytes()).hexdigest()
    project = qnx.projects.get_or_create(
        name="p6-helios-cost-evidence",
        description="P6 shot-cost evidence; no emulator or physical execution",
    )
    ref = qnx.qir.upload(
        qir=QIR.read_bytes(),
        name=f"p6-cost-{qir_hash[:12]}",
        project=project,
        description="P6 QIR for provider cost-confidence only",
    )
    estimates = qnx.qir.cost_confidence(
        programs=[ref] * len(SHOTS),
        n_shots=SHOTS,
        project=project,
        system_name="Helios-1",
    )
    rows = [
        {"shots": shots, "estimated_hqc": float(value), "confidence_percent": float(conf)}
        for shots, (value, conf) in zip(SHOTS, estimates, strict=True)
    ]
    payload = {
        "schema": "p6-helios-cost-sweep-v1",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "source_qasm": str(QASM),
        "source_qasm_sha256": qasm_hash,
        "bitcode_path": str(QIR),
        "bitcode_sha256": qir_hash,
        "syntax_checker_target": "Helios-1SC",
        "cost_endpoint_target": "Helios-1",
        "project_ref": str(getattr(project, "id", project)),
        "execution_submitted": False,
        "emulator_execution_submitted": False,
        "rows": rows,
    }
    out = ROOT / "results/nexus/cost/p6_helios_cost_sweep_20260901.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    md = ROOT / "docs/P6_HELIOS_COST_SWEEP_20260901.md"
    lines = [
        "# P6 Helios cost sweep — 2026-09-01",
        "",
        "This is provider cost-confidence evidence only. No emulator or physical",
        "execution was submitted. `Helios-1SC` is the syntax-check target; the",
        "shot-scaled HQC estimates come from the `Helios-1` costing endpoint.",
        "",
        f"Source QASM SHA-256: `{qasm_hash}`  ",
        f"Submitted bitcode SHA-256: `{qir_hash}`  ",
        "",
        "| Shots | Estimated HQC | Confidence |",
        "|---:|---:|---:|",
    ]
    lines.extend(f"| {r['shots']} | {r['estimated_hqc']} | {r['confidence_percent']}% |" for r in rows)
    lines.extend(["", "Execution submitted: **false**.", ""])
    md.write_text("\n".join(lines))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
