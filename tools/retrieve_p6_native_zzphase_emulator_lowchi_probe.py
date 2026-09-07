#!/usr/bin/env python3
"""Retrieve the completed low-chi Helios-1E emulator probe."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import qnexus as qnx

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/hardware/p6_optimized_compile_20260907/native_zzphase_helios1e_lowchi_probe.json"
OUT = ROOT / "results/hardware/p6_optimized_compile_20260907/native_zzphase_helios1e_lowchi_probe"


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
    record = json.loads(RECORD.read_text())
    job = qnx.jobs.get(id=record["job_id"])
    status = qnx.jobs.status(job)
    state = str(getattr(status.status, "value", status.status))
    if state != "COMPLETED":
        raise SystemExit(f"Job is not completed: {state}")
    refs = list(qnx.jobs.results(job))
    if len(refs) != 1:
        raise SystemExit(f"Expected one result reference, received {len(refs)}")
    result_ref = refs[0]
    payload = payload_of(result_ref.download_result())
    raw = json.dumps(payload, indent=2, ensure_ascii=False) + "\n" if not isinstance(payload, str) else payload
    OUT.mkdir(parents=True, exist_ok=True)
    raw_path = OUT / "raw_result.txt"
    raw_path.write_text(raw)
    record.update({
        "status": "RETRIEVED",
        "result_id": str(getattr(result_ref, "id", result_ref)),
        "reported_hqc": float(status.cost),
        "completed_at_utc": status.completed_time.isoformat() if status.completed_time else None,
        "raw_result_path": str(raw_path),
        "raw_result_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    })
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
