#!/usr/bin/env python3
"""Retry one chi=64 Helios-1E probe with the successful chi=32 threshold."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import qnexus as qnx

ROOT = Path(__file__).resolve().parents[1]
BITCODE = ROOT / "results/hardware/p6_optimized_compile_20260907/p6_native_zzphase.qir.bc"
OUT = ROOT / "results/hardware/p6_optimized_compile_20260907/native_zzphase_helios1e_chi64_retry.json"
JOB_NAME = "p6_native_zzphase_helios1e_chi64_retry_20260907"


def main() -> int:
    bitcode = BITCODE.read_bytes()
    project = qnx.projects.get_or_create(
        name="p6-native-zzphase-campaign",
        description="P6 native-ZZPhase hardware and emulator experiments",
    )
    artifact = qnx.qir.upload(
        qir=bitcode,
        name=JOB_NAME,
        project=project,
        description="One-shot chi=64 Helios-1E retry with forgiving truncation threshold",
    )
    config = qnx.models.HeliosConfig(
        system_name="Helios-1E",
        emulator_config=qnx.models.HeliosEmulatorConfig(
            n_qubits=62,
            simulator=qnx.models.MatrixProductStateSimulator(
                backend="auto",
                chi=64,
                zero_threshold=0.05,
            ),
            error_model=qnx.models.NoErrorModel(),
        ),
    )
    job = qnx.start_execute_job(
        programs=[artifact],
        n_shots=[1],
        max_cost=[100.0],
        n_qubits=[62],
        backend_config=config,
        project=project,
        name=JOB_NAME,
        description="P6 native-ZZPhase one-shot chi=64 emulator retry; not hardware evidence",
    )
    payload = {
        "status": "SUBMITTED",
        "submitted_at_utc": datetime.now(UTC).isoformat(),
        "target": "Helios-1E",
        "shots": 1,
        "max_cost_hqc": 100.0,
        "job_name": JOB_NAME,
        "job_id": str(getattr(job, "id", job)),
        "project_id": str(getattr(project, "id", project)),
        "qir_artifact_id": str(getattr(artifact, "id", artifact)),
        "bitcode_sha256": hashlib.sha256(bitcode).hexdigest(),
        "native_zzphase_preserved": True,
        "simulator": {"backend": "auto", "chi": 64, "zero_threshold": 0.05, "error_model": "NoErrorModel"},
        "retry_of": "d217edb0-b227-4dd1-9f2d-84abc5be5b60",
        "physical_hardware_submitted": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
