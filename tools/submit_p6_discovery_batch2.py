#!/usr/bin/env python3
"""Submit the independent second P6 discovery batch."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import qnexus as qnx


ROOT = Path(__file__).resolve().parents[1]
BITCODE = ROOT / "results/hardware/p6_helios_50shot_20260829/submitted.qir.bc"
OUT = ROOT / "hardware_campaign/p6_batch_002/job_record.json"
JOB_NAME = "p6_physical_discovery_100_batch2"
SHOTS = 100
MAX_COST = 900.0


def main() -> int:
    bitcode_hash = hashlib.sha256(BITCODE.read_bytes()).hexdigest()
    project = qnx.projects.get_or_create(
        name="p6-helios-campaign",
        description="P6 independent second discovery batch",
    )
    artifact = qnx.qir.upload(
        qir=BITCODE.read_bytes(),
        name=JOB_NAME,
        project=project,
        description="Pinned P6 QIR; independent second discovery batch; no candidate target",
    )
    job = qnx.start_execute_job(
        programs=[artifact],
        n_shots=[SHOTS],
        max_cost=[MAX_COST],
        n_qubits=[62],
        backend_config=qnx.models.HeliosConfig(system_name="Helios-1"),
        project=project,
        name=JOB_NAME,
        description="Independent P6 discovery batch; analyze separately before pooling",
    )
    payload = {
        "status": "SUBMITTED",
        "stage": "independent_discovery_batch_2",
        "submitted_at_utc": datetime.now(UTC).isoformat(),
        "target": "Helios-1",
        "shots": SHOTS,
        "max_cost_hqc": MAX_COST,
        "job_name": JOB_NAME,
        "job_id": str(getattr(job, "id", job)),
        "project_id": str(getattr(project, "id", project)),
        "qir_artifact_id": str(getattr(artifact, "id", artifact)),
        "bitcode_sha256": bitcode_hash,
        "candidate_target_used": False,
        "pooling_allowed_only_after_independent_analysis": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
