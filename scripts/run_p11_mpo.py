"""Reproducible launcher for the P11 MPO + capped-unswap solver.

Adds the SAFETY/REPRODUCIBILITY guarantees the raw ``p9solver.cli`` lacks:

* a **process-tree RSS watchdog** that terminates the run before it can OOM the
  M3 Pro (36 GB) host;
* a **deterministic manifest** (circuit SHA256, solver git commit + dirty flag,
  full option set, environment, thread budget) written before the run starts;
* a **run record** (peak RSS, wall time, termination reason) written after.

It never reads any expected bitstring, tracker answer, emulator output, or
leaked string. The solver itself is invoked with ``--expected-bitstring ""`` so
the upstream P9 default comparison is disabled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(solver_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(solver_root), *args], text=True
        ).strip()
    except Exception:
        return ""


def _tree_rss_bytes(root_pid: int) -> int:
    """Sum RSS (KB->bytes) over the process subtree rooted at root_pid via ps."""
    try:
        out = subprocess.check_output(
            ["ps", "-Ao", "pid=,ppid=,rss="], text=True
        )
    except Exception:
        return 0
    children: dict[int, list[int]] = {}
    rss: dict[int, int] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            pid, ppid, kb = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            continue
        children.setdefault(ppid, []).append(pid)
        rss[pid] = kb * 1024
    total = 0
    stack = [root_pid]
    seen = set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        total += rss.get(pid, 0)
        stack.extend(children.get(pid, []))
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--solver-root", type=Path,
                    default=Path("vendor/peaked-mpo-solver"))
    ap.add_argument("--qasm", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--tag", default="p11")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--rss-limit-gb", type=float, default=30.0,
                    help="Kill the run if process-tree RSS exceeds this (M3 Pro has 36 GB).")
    ap.add_argument("--wall-limit-s", type=float, default=None)
    ap.add_argument("--poll-s", type=float, default=5.0)
    # Any flags not recognised here are forwarded verbatim to p9solver.cli.
    args, solver_args = ap.parse_known_args()
    if solver_args and solver_args[0] == "--":
        solver_args = solver_args[1:]

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                 "NUMBA_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        env[name] = str(args.threads)
    env["PYTHONPATH"] = str(args.solver_root / "src") + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable, "-m", "p9solver.cli",
        "--qasm", str(args.qasm),
        "--outdir", str(outdir),
        "--tag", args.tag,
        "--expected-bitstring", "",
        *solver_args,
    ]

    manifest = {
        "launcher": "run_p11_mpo.py",
        "qasm": str(args.qasm),
        "qasm_sha256": _sha256(args.qasm),
        "solver_root": str(args.solver_root),
        "solver_git_commit": _git(args.solver_root, "rev-parse", "HEAD"),
        "solver_git_dirty": bool(_git(args.solver_root, "status", "--porcelain")),
        "command": cmd,
        "threads": args.threads,
        "rss_limit_gb": args.rss_limit_gb,
        "wall_limit_s": args.wall_limit_s,
        "python": sys.version.split()[0],
        "started_epoch": time.time(),
    }
    (outdir / "launcher_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Launching:", shlex.join(cmd))
    print("RSS limit:", args.rss_limit_gb, "GB | threads:", args.threads)

    limit_bytes = int(args.rss_limit_gb * (1 << 30))
    proc = subprocess.Popen(cmd, cwd=str(args.solver_root), env=env)
    peak_rss = 0
    reason = "completed"
    start = time.time()
    try:
        while True:
            ret = proc.poll()
            if ret is not None:
                reason = "completed" if ret == 0 else f"exit_{ret}"
                break
            rss = _tree_rss_bytes(proc.pid)
            peak_rss = max(peak_rss, rss)
            if rss > limit_bytes:
                reason = "rss_watchdog"
                print(f"[watchdog] RSS {rss/1e9:.1f} GB exceeded {args.rss_limit_gb} GB -> terminating")
                proc.send_signal(signal.SIGTERM)
                time.sleep(5)
                if proc.poll() is None:
                    proc.kill()
                break
            if args.wall_limit_s and (time.time() - start) > args.wall_limit_s:
                reason = "wall_limit"
                print(f"[watchdog] wall limit {args.wall_limit_s}s -> terminating")
                proc.send_signal(signal.SIGTERM)
                time.sleep(5)
                if proc.poll() is None:
                    proc.kill()
                break
            time.sleep(args.poll_s)
    except KeyboardInterrupt:
        reason = "interrupted"
        proc.send_signal(signal.SIGTERM)

    record = {
        "termination_reason": reason,
        "wall_time_s": time.time() - start,
        "peak_process_tree_rss_bytes": peak_rss,
        "peak_process_tree_rss_gb": round(peak_rss / (1 << 30), 3),
    }
    (outdir / "launcher_record.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Termination:", reason, "| peak RSS GB:", record["peak_process_tree_rss_gb"])
    return 0 if reason == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
