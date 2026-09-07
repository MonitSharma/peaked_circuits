#!/usr/bin/env python3
"""Submit one explicit P6 Helios-1E emulator pipeline probe.

This is not a recovery run: it requests one shot, uses an explicit emulator
configuration, and records the provider reference for later status/retrieval.
It cannot submit Helios-1 hardware or the P6 confirmation stage.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import qnexus as qnx


ROOT = Path(__file__).resolve().parents[1]
BITCODE = ROOT / "results/hardware/p6_helios_50shot_20260829/submitted.qir.bc"
OUT = ROOT / "results/emulator/p6_helios1e_1shot_20260906/submission.json"
JOB_NAME = "p6_helios1e_emulator_probe_1"
SHOTS = 1
MAX_COST = 100.0


def main() -> int:
    bitcode_hash = hashlib.sha256(BITCODE.read_bytes()).hexdigest()
    project = qnx.projects.get_or_create(
        name="p6-helios-emulator-probe",
        description="P6 one-shot Helios-1E pipeline probe; no hardware execution",
    )
    artifact = qnx.qir.upload(
        qir=BITCODE.read_bytes(),
        name=JOB_NAME,
        project=project,
        description="P6 one-shot emulator pipeline probe; not a solution run",
    )
    config = qnx.models.HeliosConfig(
        system_name="Helios-1E",
        emulator_config=qnx.models.HeliosEmulatorConfig(
            n_qubits=62,
            simulator=qnx.models.MatrixProductStateSimulator(),
            error_model=qnx.models.NoErrorModel(),
        ),
    )
    job = qnx.start_execute_job(
        programs=[artifact],
        n_shots=[SHOTS],
        max_cost=[MAX_COST],
        n_qubits=[62],
        backend_config=config,
        project=project,
        name=JOB_NAME,
        description="Helios-1E emulator pipeline probe; physical Helios-1 forbidden",
    )
    payload = {
        "status": "SUBMITTED",
        "submitted_at_utc": datetime.now(UTC).isoformat(),
        "target": "Helios-1E",
        "shots": SHOTS,
        "max_cost_hqc": MAX_COST,
        "job_name": JOB_NAME,
        "job_id": str(getattr(job, "id", job)),
        "project_id": str(getattr(project, "id", project)),
        "qir_artifact_id": str(getattr(artifact, "id", artifact)),
        "bitcode_sha256": bitcode_hash,
        "hardware_execution": False,
        "purpose": "pipeline_probe_only",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
