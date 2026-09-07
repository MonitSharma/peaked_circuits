#!/usr/bin/env python3
"""Submit the authorized second independent 50-shot native-ZZPhase P6 run."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import qnexus as qnx

ROOT = Path(__file__).resolve().parents[1]
BITCODE = ROOT / "results/hardware/p6_optimized_compile_20260907/p6_native_zzphase.qir.bc"
OUT = ROOT / "results/hardware/p6_optimized_compile_20260907/native_zzphase_50shot_batch2_submission.json"
JOB_NAME = "p6_native_zzphase_50shot_batch2_20260907"
SHOTS = 50
MAX_COST = 500.0


def main() -> int:
    bitcode = BITCODE.read_bytes()
    project = qnx.projects.get_or_create(
        name="p6-native-zzphase-campaign",
        description="P6 native-ZZPhase hardware experiment",
    )
    artifact = qnx.qir.upload(
        qir=bitcode,
        name=JOB_NAME,
        project=project,
        description="Second independent exploratory P6 native-ZZPhase 50-shot Helios-1 run",
    )
    job = qnx.start_execute_job(
        programs=[artifact],
        n_shots=[SHOTS],
        max_cost=[MAX_COST],
        n_qubits=[62],
        backend_config=qnx.models.HeliosConfig(system_name="Helios-1"),
        project=project,
        name=JOB_NAME,
        description="Second independent P6 native-ZZPhase 50-shot exploratory hardware run",
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
        "bitcode_path": str(BITCODE),
        "bitcode_sha256": hashlib.sha256(bitcode).hexdigest(),
        "native_zzphase_preserved": True,
        "independent_experiment": True,
        "same_qir_as_batch1": True,
        "candidate_target_used": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
