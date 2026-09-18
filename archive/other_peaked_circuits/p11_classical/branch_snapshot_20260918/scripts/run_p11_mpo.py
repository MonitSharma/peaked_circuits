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

ROOT = Path(__file__).resolve().parents[1]


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


def _tree_vmhwm_bytes(root_pid: int) -> int:
    """Read Linux VmHWM for the process tree when available."""
    total = 0
    try:
        out = subprocess.check_output(["ps", "-Ao", "pid=,ppid="], text=True)
        parents = {int(row.split()[0]): int(row.split()[1]) for row in out.splitlines() if len(row.split()) >= 2}
        included = {root_pid}
        changed = True
        while changed:
            changed = False
            for pid, parent in parents.items():
                if parent in included and pid not in included:
                    included.add(pid)
                    changed = True
        for pid in included:
            status = Path(f"/proc/{pid}/status")
            if status.exists():
                for line in status.read_text().splitlines():
                    if line.startswith("VmHWM:"):
                        total += int(line.split()[1]) * 1024
                        break
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass
    return total


def _physical_cpu_ids() -> list[int]:
    identities: dict[tuple[str, str], int] = {}
    for cpu_path in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
        try:
            cpu = int(cpu_path.name[3:])
            package = (cpu_path / "topology/physical_package_id").read_text().strip()
            core = (cpu_path / "topology/core_id").read_text().strip()
        except (OSError, ValueError):
            continue
        identities.setdefault((package, core), cpu)
    if identities:
        return sorted(identities.values())
    return list(range(os.cpu_count() or 1))


def _remove_forwarded_flag(arguments: list[str], flag: str) -> list[str]:
    cleaned: list[str] = []
    skip = False
    for argument in arguments:
        if skip:
            skip = False
            continue
        if argument == flag:
            skip = True
        elif argument.startswith(flag + "="):
            continue
        else:
            cleaned.append(argument)
    return cleaned


def _parse_cpu_list(value: str | None) -> set[int] | None:
    if not value:
        return None
    cpus: set[int] = set()
    for item in value.split(","):
        bounds = item.strip().split("-", 1)
        if len(bounds) == 1:
            cpus.add(int(bounds[0]))
        else:
            cpus.update(range(int(bounds[0]), int(bounds[1]) + 1))
    return cpus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--solver-root", type=Path, default=None)
    ap.add_argument("--qasm", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--tag", default="p11")
    ap.add_argument("--threads", default="auto")
    ap.add_argument("--cpu-list", default=None)
    ap.add_argument("--numa-node", default=None)
    ap.add_argument("--rss-limit-gb", type=float, default=None,
                    help="Process-tree RSS guard; HPC defaults to 450 GB, profiles should override it.")
    ap.add_argument("--rss-soft-gb", type=float, default=None,
                    help="Process-tree RSS warning threshold; never terminates a run.")
    ap.add_argument("--wall-limit-s", type=float, default=None)
    ap.add_argument("--poll-s", type=float, default=5.0)
    # Any flags not recognised here are forwarded verbatim to p9solver.cli.
    args, solver_args = ap.parse_known_args()
    if solver_args and solver_args[0] == "--":
        solver_args = solver_args[1:]

    solver_root = (args.solver_root or ROOT / "external/peaked-mpo-solver").expanduser().resolve()
    if not (solver_root / "src/p9solver/cli.py").is_file():
        raise SystemExit(f"p9solver not found under {solver_root}; run hpc/bootstrap_solver.sh")
    threads = len(_physical_cpu_ids()) if args.threads == "auto" else int(args.threads)
    rss_limit_gb = args.rss_limit_gb if args.rss_limit_gb is not None else 450.0
    rss_soft_gb = args.rss_soft_gb
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                 "NUMBA_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        env[name] = str(threads)
    # Numba's cache locator cannot resolve the symlinked/relocated solver
    # package on this macOS host and otherwise raises before the first gate
    # (or, in older stacks, fails inside a native cached kernel).  Keep cache
    # files in a real writable directory by default; callers can override it.
    if not env.get("NUMBA_CACHE_DIR"):
        numba_cache = outdir / ".numba_cache"
        numba_cache.mkdir(parents=True, exist_ok=True)
        env["NUMBA_CACHE_DIR"] = str(numba_cache)
    env["PYTHONPATH"] = str(solver_root / "src") + os.pathsep + env.get("PYTHONPATH", "")

    solver_args = _remove_forwarded_flag(list(solver_args), "--expected-bitstring")
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
        "solver_root": str(solver_root),
        "solver_git_commit": _git(solver_root, "rev-parse", "HEAD"),
        "solver_git_dirty": bool(_git(solver_root, "status", "--porcelain")),
        "command": cmd,
        "threads": threads,
        "numba_cache_dir": env.get("NUMBA_CACHE_DIR"),
        "cpu_list": args.cpu_list,
        "numa_node": args.numa_node,
        "rss_limit_gb": rss_limit_gb,
        "rss_soft_gb": rss_soft_gb,
        "wall_limit_s": args.wall_limit_s,
        "python": sys.version.split()[0],
        "started_epoch": time.time(),
    }
    (outdir / "launcher_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Launching:", shlex.join(cmd))
    print("RSS limit:", rss_limit_gb, "GB | threads:", threads)

    limit_bytes = int(rss_limit_gb * (1 << 30))
    def forward_signal(signum, _frame):
        if proc.poll() is None:
            proc.send_signal(signum)

    cpu_set = _parse_cpu_list(args.cpu_list)
    def set_affinity() -> None:
        if cpu_set and hasattr(os, "sched_setaffinity"):
            os.sched_setaffinity(0, cpu_set)

    proc = subprocess.Popen(cmd, cwd=str(solver_root), env=env, start_new_session=True, preexec_fn=set_affinity)
    signal.signal(signal.SIGTERM, forward_signal)
    signal.signal(signal.SIGINT, forward_signal)
    peak_rss = 0
    peak_vmhwm = 0
    soft_rss_exceeded = False
    reason = "completed"
    start = time.monotonic()
    try:
        while True:
            ret = proc.poll()
            if ret is not None:
                reason = "completed" if ret == 0 else f"exit_{ret}"
                break
            rss = _tree_rss_bytes(proc.pid)
            peak_rss = max(peak_rss, rss)
            if rss_soft_gb is not None and rss > rss_soft_gb * (1 << 30):
                soft_rss_exceeded = True
            peak_vmhwm = max(peak_vmhwm, _tree_vmhwm_bytes(proc.pid))
            if rss > limit_bytes:
                reason = "rss_watchdog"
                print(f"[watchdog] RSS {rss/1e9:.1f} GB exceeded {args.rss_limit_gb} GB -> terminating")
                proc.send_signal(signal.SIGTERM)
                time.sleep(5)
                if proc.poll() is None:
                    proc.kill()
                break
            if args.wall_limit_s and (time.monotonic() - start) > args.wall_limit_s:
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
        "wall_time_s": time.monotonic() - start,
        "peak_process_tree_rss_bytes": peak_rss,
        "peak_process_tree_rss_gb": round(peak_rss / (1 << 30), 3),
        "peak_process_tree_vmhwm_bytes": peak_vmhwm,
        "peak_process_tree_vmhwm_gb": round(peak_vmhwm / (1 << 30), 3),
        "rss_soft_gb": rss_soft_gb,
        "rss_soft_exceeded": soft_rss_exceeded,
    }
    (outdir / "launcher_record.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Termination:", reason, "| peak RSS GB:", record["peak_process_tree_rss_gb"])
    return 0 if reason == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
