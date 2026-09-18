#!/usr/bin/env python3
"""Submit one isolated P6 Helios-1 hardware quota probe."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import qnexus as qnx


ROOT = Path(__file__).resolve().parents[1]
BITCODE = ROOT / "results/hardware/p6_helios_50shot_20260829/submitted.qir.bc"
OUT = ROOT / "results/hardware/p6_helios1_1shot_20260906_retry3/probe.json"
JOB_NAME = "p6_helios1_hardware_probe_1"
SHOTS = 1
MAX_COST = 20.0


def main() -> int:
    bitcode_hash = hashlib.sha256(BITCODE.read_bytes()).hexdigest()
    project = qnx.projects.get_or_create(
        name="p6-helios-hardware-probe",
        description="P6 one-shot hardware quota probe; separate from discovery campaign",
    )
    artifact = qnx.qir.upload(
        qir=BITCODE.read_bytes(),
        name=JOB_NAME,
        project=project,
        description="P6 one-shot Helios-1 hardware quota probe",
    )
    job = qnx.start_execute_job(
        programs=[artifact],
        n_shots=[SHOTS],
        max_cost=[MAX_COST],
        n_qubits=[62],
        backend_config=qnx.models.HeliosConfig(system_name="Helios-1"),
        project=project,
        name=JOB_NAME,
        description="One-shot P6 hardware quota probe; not the 100-shot discovery job",
    )
    payload = {
        "status": "SUBMITTED",
        "submitted_at_utc": datetime.now(UTC).isoformat(),
        "target": "Helios-1",
        "shots": SHOTS,
        "max_cost_hqc": MAX_COST,
        "job_name": JOB_NAME,
        "job_id": str(getattr(job, "id", job)),
        "project_id": str(getattr(project, "id", project)),
        "qir_artifact_id": str(getattr(artifact, "id", artifact)),
        "bitcode_sha256": bitcode_hash,
        "probe_only": True,
        "planned_discovery_untouched": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
