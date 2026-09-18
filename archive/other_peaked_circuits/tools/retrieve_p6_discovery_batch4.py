#!/usr/bin/env python3
"""Retrieve and preserve the completed independent fourth P6 discovery batch."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import qnexus as qnx

ROOT = Path(__file__).resolve().parents[1]
JOB_ID = "0da697e8-de3a-4034-a0b2-1c9ff350c7b5"
OUT = ROOT / "results/hardware/p6_helios_100shot_20260907_batch4"
RECORD = ROOT / "hardware_campaign/p6_batch_004/job_record.json"


def payload_of(value: Any) -> Any:
    if hasattr(value, "results") and isinstance(value.results, str):
        return value.results
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    return {"type": type(value).__name__, "representation": str(value)}


def main() -> int:
    job = qnx.jobs.get(id=JOB_ID)
    status = qnx.jobs.status(job)
    if str(getattr(status.status, "value", status.status)) != "COMPLETED":
        raise SystemExit(f"Job is not completed: {status}")
    refs = list(qnx.jobs.results(job))
    if len(refs) != 1:
        raise SystemExit(f"Expected one result reference, received {len(refs)}")
    result_ref = refs[0]
    payload = payload_of(result_ref.download_result())
    raw = json.dumps(payload, indent=2, ensure_ascii=False) + "\n" if not isinstance(payload, str) else payload
    OUT.mkdir(parents=True, exist_ok=True)
    raw_path = OUT / "raw_result.json"
    raw_path.write_text(raw)
    raw_hash = hashlib.sha256(raw.encode()).hexdigest()
    record = json.loads(RECORD.read_text())
    record.update(
        {
            "result_id": str(getattr(result_ref, "id", result_ref)),
            "returned_shots": 100,
            "reported_hqc": float(status.cost),
            "queued_at_utc": status.queued_time.isoformat() if status.queued_time else None,
            "running_at_utc": status.running_time.isoformat() if status.running_time else None,
            "completed_at_utc": status.completed_time.isoformat() if status.completed_time else None,
            "raw_result_path": str(raw_path.relative_to(ROOT)),
            "raw_result_sha256": raw_hash,
            "status": "RETRIEVED",
        }
    )
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"job_id": JOB_ID, "result_id": record["result_id"], "raw_result": str(raw_path), "raw_sha256": raw_hash, "reported_hqc": record["reported_hqc"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
