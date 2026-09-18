#!/usr/bin/env python3
"""P9-only HPC calibration wrapper; the P11 launcher never uses an oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

P9_SHA256 = "cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35"
P9_EXPECTED = "01101110111001100000100000001010011100101101010111110111"


def git_value(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--solver-root", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--threads", type=int, required=True)
    # Match the published MacBook P9 protocol.  A lower bond dimension is a
    # diagnostic stress test, not a reproducibility run.
    parser.add_argument("--max-bond", type=int, default=8192)
    parser.add_argument("--cutoff", type=float, default=0.0006)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--unswap-threshold", type=float, default=1_000_000.0)
    parser.add_argument("--no-progress-limit", type=int, default=20)
    parser.add_argument("--max-work-gates", type=int)
    parser.add_argument("--unswap-select-mode", default="bond")
    parser.add_argument("--unswap-pair-lookahead-limit", type=int, default=8)
    parser.add_argument("--no-parallel-rewire", action="store_true")
    args = parser.parse_args()

    # Resolve paths before spawning p9solver because the child process runs
    # with cwd=solver_root. Relative QASM paths would otherwise be interpreted
    # relative to the external solver checkout.
    args.qasm = args.qasm.resolve()
    args.solver_root = args.solver_root.resolve()
    args.outdir = args.outdir.resolve()

    raw = args.qasm.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    digest = hashlib.sha256(normalized).hexdigest()
    if digest != P9_SHA256:
        raise SystemExit(
            f"P9 calibration wrapper refuses a non-P9 circuit: normalized sha256={digest}"
        )
    env = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS", "BLIS_NUM_THREADS"):
        env[name] = str(args.threads)
    env["PYTHONPATH"] = str(args.solver_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    command = [
        sys.executable, "-m", "p9solver.cli",
        "--qasm", str(args.qasm), "--outdir", str(args.outdir),
        "--tag", args.tag, "--samples", str(args.samples),
        "--expected-bitstring", P9_EXPECTED, "--max-bond", str(args.max_bond),
        "--cutoff", str(args.cutoff), "--unswap-threshold", str(args.unswap_threshold),
        "--abort-after-no-progress-unswap-cycles", str(args.no_progress_limit),
        "--unswap-select-mode",
        args.unswap_select_mode, "--unswap-pair-lookahead-limit",
        str(args.unswap_pair_lookahead_limit),
    ]
    if args.max_work_gates is not None:
        command.extend(["--max-work-gates", str(args.max_work_gates)])
    if args.no_parallel_rewire:
        command.append("--no-parallel-rewire")
    args.outdir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "qasm_sha256": digest,
        "expected_bitstring_scope": "P9_CALIBRATION_ONLY",
        "command": command,
        "threads": args.threads,
        "thread_env": {name: env.get(name, "") for name in (
            "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
            "NUMBA_NUM_THREADS", "BLIS_NUM_THREADS", "PYTHONUNBUFFERED",
        )},
        "python": sys.version,
        "repo_git_commit": git_value(Path(__file__).resolve().parents[1], "rev-parse", "HEAD"),
        "repo_git_dirty": bool(git_value(Path(__file__).resolve().parents[1], "status", "--porcelain")),
        "solver_git_commit": git_value(args.solver_root, "rev-parse", "HEAD"),
        "solver_git_dirty": bool(git_value(args.solver_root, "status", "--porcelain")),
        "cpu_affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else [],
    }
    try:
        provenance["numactl_show"] = subprocess.check_output(["numactl", "--show"], text=True, stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        provenance["numactl_show"] = ""
    (args.outdir / f"{args.tag}.p9_manifest.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return subprocess.run(command, cwd=args.solver_root, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
