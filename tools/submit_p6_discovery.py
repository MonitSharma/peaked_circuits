#!/usr/bin/env python3
"""Submit only the gated P6 100-shot discovery job.

This command deliberately has no confirmation-job path. Confirmation requires
an analyzed and frozen discovery candidate plus a separate user decision.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import qnexus as qnx


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "hardware_campaign/p6_batch_001/protocol.json"
RECORD = ROOT / "hardware_campaign/p6_batch_001/job_records/discovery.json"
BITCODE = ROOT / "results/hardware/p6_helios_50shot_20260829/submitted.qir.bc"
JOB_NAME = "p6_physical_discovery_100"
SHOTS = 100
MAX_COST = 900.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    protocol = json.loads(PROTOCOL.read_text())
    stage = next(item for item in protocol["stages"] if item["name"] == "discovery")
    record = json.loads(RECORD.read_text())
    if record["status"] not in {"NOT_SUBMITTED", "REJECTED_PREQUEUE"} or record["job_id"] is not None:
        raise SystemExit("Discovery record is not retryable; refusing to submit.")
    if stage["shots"] != SHOTS or stage["max_cost_hqc"] != MAX_COST:
        raise SystemExit("Pinned discovery shot count or max cost does not match.")
    if sha256(BITCODE) != protocol["submitted_bitcode_sha256"]:
        raise SystemExit("Pinned P6 bitcode hash mismatch; refusing to submit.")

    project = qnx.projects.get_or_create(
        name="p6-helios-campaign",
        description="P6 gated hardware campaign; discovery stage only",
    )
    artifact = qnx.qir.upload(
        qir=BITCODE.read_bytes(),
        name=JOB_NAME,
        project=project,
        description="Pinned P6 discovery QIR; 100 shots; confirmation is separately gated",
    )
    job = qnx.start_execute_job(
        programs=[artifact],
        n_shots=[SHOTS],
        backend_config=qnx.models.HeliosConfig(system_name="Helios-1"),
        project=project,
        name=JOB_NAME,
        max_cost=MAX_COST,
    )
    now = datetime.now(UTC).isoformat()
    record.setdefault("submission_attempts", []).append(
        {"attempted_at_utc": now, "outcome": "provider_accepted", "job_id": str(getattr(job, "id", job))}
    )
    record.update(
        {
            "job_id": str(getattr(job, "id", job)),
            "result_id": None,
            "qir_artifact_id": str(getattr(artifact, "id", artifact)),
            "submitted_at_utc": now,
            "status": "SUBMITTED",
            "notes": "Discovery submitted only. Retrieve and analyze the first 100 shots; do not submit confirmation automatically.",
        }
    )
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"job_id": record["job_id"], "job_name": JOB_NAME, "shots": SHOTS, "max_cost_hqc": MAX_COST}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
