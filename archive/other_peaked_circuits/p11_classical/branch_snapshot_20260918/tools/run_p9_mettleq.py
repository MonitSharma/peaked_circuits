#!/usr/bin/env python3
"""Run a reproducible MettleQ midpoint-MPO P9 experiment.

The MettleQ checkout is intentionally supplied from outside this repository so
that this harness can test a local package checkout without copying or
overwriting its files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ORACLE = "01101110111001100000100000001010011100101101010111110111"
DEFAULT_QASM_NAME = "peaked_circuit_P9_Hqap_56x1917.qasm"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(root: Path, *arguments: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *arguments], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _package_versions(python: Path, mettleq_root: Path) -> dict[str, str]:
    code = (
        "import json,platform,sys; "
        "names=['mettleq','numpy','scipy','quimb','qiskit']; "
        "out={'python':sys.version,'platform':platform.platform()}; "
        "\nfor name in names:\n"
        "  try:\n"
        "    mod=__import__(name); out[name]=getattr(mod,'__version__','unknown')\n"
        "  except Exception as error:\n"
        "    out[name]=f'{type(error).__name__}: {error}'\n"
        "print(json.dumps(out))"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(mettleq_root / "src"), env.get("PYTHONPATH")) if value
    )
    return json.loads(subprocess.check_output([str(python), "-c", code], env=env, text=True))


def _find_qasm(root: Path) -> Path:
    candidates = [
        root / "src" / "mettleq" / "datasets" / DEFAULT_QASM_NAME,
        root / ".venv" / "lib" / "python3.13" / "site-packages" / "mettleq" / "datasets" / DEFAULT_QASM_NAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"could not find {DEFAULT_QASM_NAME} under {root}")


def _process_tree_rss_bytes(pid: int) -> int:
    """Return the current RSS of a process and its descendants on macOS/Linux."""
    try:
        output = subprocess.check_output(
            ["ps", "-axo", "pid=,ppid=,rss="], text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return 0
    rows: dict[int, tuple[int, int]] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            child, parent, rss_kib = (int(value) for value in fields)
        except ValueError:
            continue
        rows[child] = (parent, rss_kib)
    included = {pid}
    changed = True
    while changed:
        changed = False
        for child, (parent, _rss_kib) in rows.items():
            if child not in included and parent in included:
                included.add(child)
                changed = True
    return sum(rows[child][1] for child in included if child in rows) * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mettleq-root", type=Path, required=True)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--qasm", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--max-bond", type=int, default=8192)
    parser.add_argument("--cutoff", type=float, default=0.002)
    parser.add_argument("--unswap-threshold", type=float, default=1e6)
    parser.add_argument("--center-ratio", type=float, default=0.5)
    parser.add_argument("--max-unswap-iterations", type=int, default=20)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--sabre-trials", type=int, default=90)
    parser.add_argument("--post-sabre-trials", type=int, default=50)
    parser.add_argument("--no-progress-limit", type=int, default=20)
    parser.add_argument("--max-work-gates", type=int, default=None)
    parser.add_argument("--veclib-threads", type=int, default=1)
    parser.add_argument("--omp-threads", type=int, default=1)
    parser.add_argument("--svd-isolation-min-elements", type=int, default=None)
    parser.add_argument(
        "--compression-method",
        choices=("svd", "isvd", "svds", "rsvd"),
        default="svd",
    )
    parser.add_argument("--dtype", choices=("complex128", "complex64"), default="complex128")
    args = parser.parse_args()

    root = args.mettleq_root.expanduser().resolve()
    # Preserve a virtual environment's interpreter symlink. Resolving it can
    # silently replace the venv with the system/uv interpreter and lose its
    # installed scientific packages.
    python = Path(
        os.path.abspath(os.fspath((args.python or root / ".venv" / "bin" / "python").expanduser()))
    )
    qasm = (args.qasm or _find_qasm(root)).expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not python.exists():
        parser.error(f"Python interpreter does not exist: {python}")
    if not qasm.exists():
        parser.error(f"P9 QASM does not exist: {qasm}")

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(root / "src"), env.get("PYTHONPATH")) if value
    )
    env["VECLIB_MAXIMUM_THREADS"] = str(args.veclib_threads)
    env["OMP_NUM_THREADS"] = str(args.omp_threads)
    if args.svd_isolation_min_elements is not None:
        env["METTLEQ_MPO_SVD_ISOLATION_MIN_ELEMENTS"] = str(
            args.svd_isolation_min_elements
        )
    command = [
        str(python),
        "-m",
        "mettleq.midpoint_mpo",
        "--qasm",
        str(qasm),
        "--output-dir",
        str(output),
        "--shots",
        str(args.shots),
        "--expected-bitstring",
        ORACLE,
        "--max-bond",
        str(args.max_bond),
        "--cutoff",
        str(args.cutoff),
        "--unswap-threshold",
        str(args.unswap_threshold),
        "--center-ratio",
        str(args.center_ratio),
        "--max-unswap-iterations",
        str(args.max_unswap_iterations),
        "--seed",
        str(args.seed),
        "--sabre-trials",
        str(args.sabre_trials),
        "--post-sabre-trials",
        str(args.post_sabre_trials),
        "--no-progress-limit",
        str(args.no_progress_limit),
    ]
    if args.max_work_gates is not None:
        command.extend(["--max-work-gates", str(args.max_work_gates)])
    command.extend([
        "--compression-method",
        args.compression_method,
        "--dtype",
        args.dtype,
    ])
    manifest = {
        "benchmark": "p9_mettleq_midpoint_mpo",
        "created_at_epoch": time.time(),
        "recovery_repo": str(Path(__file__).resolve().parents[1]),
        "mettleq_root": str(root),
        "mettleq_git_commit": _git(root, "rev-parse", "HEAD"),
        "mettleq_git_dirty": bool(_git(root, "status", "--porcelain")),
        "python": str(python),
        "environment": _package_versions(python, root),
        "qasm": str(qasm),
        "qasm_sha256": _sha256(qasm),
        "expected_bitstring": ORACLE,
        "command": command,
        "thread_environment": {
            "VECLIB_MAXIMUM_THREADS": args.veclib_threads,
            "OMP_NUM_THREADS": args.omp_threads,
            "METTLEQ_MPO_SVD_ISOLATION_MIN_ELEMENTS": args.svd_isolation_min_elements,
        },
        "options": {
            "shots": args.shots,
            "max_bond": args.max_bond,
            "cutoff": args.cutoff,
            "unswap_threshold": args.unswap_threshold,
            "center_ratio": args.center_ratio,
            "max_unswap_iterations": args.max_unswap_iterations,
            "seed": args.seed,
            "sabre_trials": args.sabre_trials,
            "post_sabre_trials": args.post_sabre_trials,
            "no_progress_limit": args.no_progress_limit,
            "max_work_gates": args.max_work_gates,
            "compression_method": args.compression_method,
            "dtype": args.dtype,
        },
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version,
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    started = time.perf_counter()
    peak_rss_bytes = 0
    completed = subprocess.Popen(command, env=env, start_new_session=True)
    status = "completed"
    termination_reason = None
    try:
        while completed.poll() is None:
            peak_rss_bytes = max(peak_rss_bytes, _process_tree_rss_bytes(completed.pid))
            time.sleep(0.25)
    except KeyboardInterrupt:
        status = "interrupted"
        termination_reason = "harness_keyboard_interrupt"
        try:
            os.killpg(completed.pid, 15)
        except ProcessLookupError:
            pass
        try:
            completed.wait(timeout=10)
        except subprocess.TimeoutExpired:
            status = "interrupted_force_kill"
            termination_reason = "harness_keyboard_interrupt_child_did_not_exit"
            try:
                os.killpg(completed.pid, 9)
            except ProcessLookupError:
                pass
            completed.wait()
    peak_rss_bytes = max(peak_rss_bytes, _process_tree_rss_bytes(completed.pid))
    manifest.update(
        {
            "status": status,
            "termination_reason": termination_reason,
            "returncode": completed.returncode,
            "wall_time_s": time.perf_counter() - started,
            "peak_rss_bytes": peak_rss_bytes,
            "finished_at_epoch": time.time(),
        }
    )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
