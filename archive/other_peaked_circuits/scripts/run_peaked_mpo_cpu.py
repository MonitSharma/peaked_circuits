"""Run the upstream CPU MPO + unswapping solver from this project.

The upstream solver is kept as a separately fetched, Apache-2.0 repository so
its research implementation remains auditable.  This launcher supplies the
project circuit, removes the upstream P9-only expected-bitstring default, and
sets one consistent thread budget before NumPy/BLAS is imported.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QASM = ROOT / "circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm"
DEFAULT_SOLVER_ROOTS = (
    ROOT / "vendor/peaked-mpo-solver",
    ROOT / "_upstream_peaked_mpo_solver",
)


def _available_cpus() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


def _physical_cpus() -> int:
    """Return physical cores visible to the process when Linux exposes topology."""
    topology_root = Path("/sys/devices/system/cpu")
    identities: set[tuple[str, str]] = set()
    for cpu_path in topology_root.glob("cpu[0-9]*"):
        try:
            package = (cpu_path / "topology/physical_package_id").read_text().strip()
            core = (cpu_path / "topology/core_id").read_text().strip()
        except OSError:
            continue
        identities.add((package, core))
    available = _available_cpus()
    if identities:
        return max(1, min(len(identities), available))
    return available


def _find_solver_root(value: str | None) -> Path:
    candidates = ((Path(value),) if value else DEFAULT_SOLVER_ROOTS)
    for candidate in candidates:
        source = candidate / "src"
        if (source / "p9solver" / "cli.py").is_file():
            return candidate.resolve()
    searched = ", ".join(str(path) for path in candidates)
    raise SystemExit(
        "Could not find the CPU MPO solver. Fetch it with:\n"
        "  git clone --depth 1 https://github.com/alexgalda-m/peaked-mpo-solver.git "
        f"{DEFAULT_SOLVER_ROOTS[0]}\nSearched: {searched}"
    )


def _has_option(arguments: list[str], name: str) -> bool:
    return any(argument == name or argument.startswith(name + "=") for argument in arguments)


def _value_after(arguments: list[str], name: str, default: str) -> str:
    for index, argument in enumerate(arguments):
        if argument == name and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(name + "="):
            return argument.split("=", 1)[1]
    return default


def _set_thread_budget(threads: int) -> dict[str, str]:
    values = {name: str(threads) for name in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "BLIS_NUM_THREADS",
        "NUMBA_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    )}
    os.environ.update(values)
    return values


def _metadata_path(arguments: list[str]) -> Path:
    outdir = Path(_value_after(arguments, "--outdir", "runs"))
    tag = _value_after(arguments, "--tag", "cpu")
    return outdir / tag / "cpu_launcher.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project launcher for the CPU-oriented peaked-circuit MPO solver."
    )
    parser.add_argument("--solver-root", help="Path to a checkout of alexgalda-m/peaked-mpo-solver.")
    parser.add_argument(
        "--threads",
        default="auto",
        help="BLAS/Numba thread budget; default is the CPUs available to this process.",
    )
    parsed, solver_args = parser.parse_known_args()
    solver_args = list(solver_args)

    solver_root = _find_solver_root(parsed.solver_root)
    threads = _physical_cpus() if parsed.threads == "auto" else int(parsed.threads)
    if threads < 1:
        raise SystemExit("--threads must be 'auto' or a positive integer")
    thread_environment = _set_thread_budget(threads)

    if not _has_option(solver_args, "--qasm"):
        solver_args.extend(["--qasm", str(DEFAULT_QASM)])
    if not _has_option(solver_args, "--outdir"):
        solver_args.extend(["--outdir", str(ROOT / "results/simulation")])
    if not _has_option(solver_args, "--tag"):
        solver_args.extend(["--tag", "p12_cpu"])
    if not _has_option(solver_args, "--expected-bitstring"):
        # p9solver ships with P9's known answer as its CLI default.  P12 is an
        # unsolved benchmark, so comparison must be explicitly disabled.
        solver_args.extend(["--expected-bitstring", ""])

    metadata_path = _metadata_path(solver_args)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps({
        "solver_root": str(solver_root),
        "solver_command": [sys.executable, "-m", "p9solver.cli", *solver_args],
        "thread_budget": threads,
        "thread_environment": thread_environment,
        "cwd": str(ROOT),
    }, indent=2) + "\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(solver_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, "-m", "p9solver.cli", *solver_args]
    print("Launching:", shlex.join(command))
    print("Solver root:", solver_root)
    print("Thread budget:", threads)
    return subprocess.run(command, cwd=ROOT, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
