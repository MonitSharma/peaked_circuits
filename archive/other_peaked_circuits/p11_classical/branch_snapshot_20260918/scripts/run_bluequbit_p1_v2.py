#!/usr/bin/env python3
"""Resumable, Mac-only P1 v2 campaign orchestrator.

The default is a dry run.  This wrapper never knows or requests a challenge
answer and contains no HPC, cloud, QPU, or P9 stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QASM = Path("<local-user>/Downloads/P1_little_dimple.qasm")
OUT = ROOT / "results/bluequbit_p1_v2"
EXPECTED_SHA256 = "0a02afffbdcf6755d5ed16b3a10cddd40cde4ee072d6072dbe7013e1c42f2ff8"

STAGES = {
    "AUDIT": [OUT / "AUDIT.json"],
    "PROFILE": [OUT / "profile/circuit.json", OUT / "profile/clifford_proximity.json", OUT / "profile/lightcones.json"],
    "COMPILE": [OUT / "compile/summary.json"],
    "SPARSE_SMOKE": [OUT / "sparse/k4096/run.json"],
    "SPARSE_LADDER": [OUT / "sparse/convergence.json"],
    "PPS_SMOKE": [OUT / "pauli/convergence.json"],
    "BP_SMOKE": [OUT / "belief/smoke.json"],
    "MPS_WEAK_SIGNAL": [ROOT / "results/bluequbit_p1/distillation/CONSENSUS.json"],
    "AMPLITUDE_PATH": [OUT / "amplitude/path.json"],
    "CONSENSUS": [OUT / "consensus/candidates.json"],
}


def qasm_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"schema": "bluequbit-p1-v2-campaign-state-v1", "stages": {}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=OUT / "CAMPAIGN_STATE.json")
    parser.add_argument("--stage", choices=list(STAGES), action="append")
    parser.add_argument("--execute", action="store_true", help="execute only the small local PROFILE/COMPILE commands")
    parser.add_argument("--reset-stage", action="append", default=[])
    args = parser.parse_args()
    if platform.system() != "Darwin":
        raise SystemExit("P1 v2 campaign is Mac-only")
    if not QASM.exists():
        raise SystemExit(f"missing local P1 input: {QASM}")
    actual = qasm_sha256(QASM)
    if actual != EXPECTED_SHA256:
        raise SystemExit(f"P1 SHA256 changed: {actual}")
    state = load_state(args.state)
    state.update({"schema": "bluequbit-p1-v2-campaign-state-v1", "qasm_path": str(QASM), "qasm_sha256": actual, "blind": True, "hpc_jobs_launched": False, "qpu_or_cloud_jobs_launched": False})
    selected = args.stage or list(STAGES)
    for stage in selected:
        artifacts = STAGES[stage]
        valid = all(path.exists() and path.stat().st_size > 0 for path in artifacts)
        if stage not in args.reset_stage and valid:
            state["stages"][stage] = {"status": "COMPLETE_ARTIFACT_REUSED", "artifacts": [str(p) for p in artifacts]}
            print(f"{stage}: skip (valid artifacts)")
            continue
        state["stages"][stage] = {"status": "PENDING", "artifacts": [str(p) for p in artifacts]}
        print(f"{stage}: pending ({'execute' if args.execute else 'dry-run'})")
        if args.execute and stage == "PROFILE":
            subprocess.run([sys.executable, str(ROOT / "scripts/profile_bluequbit_p1_v2.py"), str(QASM), str(OUT / "profile")], cwd=ROOT, check=True)
        elif args.execute and stage == "COMPILE":
            subprocess.run([sys.executable, str(ROOT / "scripts/compile_bluequbit_p1_v2.py"), str(QASM), str(OUT / "compile/summary.json")], cwd=ROOT, check=True)
        if all(path.exists() and path.stat().st_size > 0 for path in artifacts):
            state["stages"][stage]["status"] = "COMPLETE"
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
