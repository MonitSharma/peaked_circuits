"""Collect reproducible CPU-server and numerical-library metadata.

This probe is intentionally read-only.  Run it on the machine that will execute
the MPO solver and send the JSON output back with secrets removed.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


def _available_cpus() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


def _memory_bytes() -> int | None:
    if sys.platform.startswith("linux"):
        try:
            text = Path("/proc/meminfo").read_text()
            match = re.search(r"^MemTotal:\s+(\d+)\s+kB", text, re.MULTILINE)
            if match:
                return int(match.group(1)) * 1024
        except OSError:
            pass
    if sys.platform == "darwin":
        try:
            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return None


def _cpu_model() -> str | None:
    if sys.platform.startswith("linux"):
        try:
            text = Path("/proc/cpuinfo").read_text(errors="replace")
            match = re.search(r"^(?:model name|Hardware)\s*:\s*(.+)$", text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        except OSError:
            pass
    value = platform.processor() or platform.machine()
    return value or None


def _command_json(command: list[str]) -> Any | None:
    if shutil.which(command[0]) is None:
        return None
    try:
        return json.loads(subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL))
    except (OSError, json.JSONDecodeError, subprocess.SubprocessError):
        return None


def _package_versions() -> dict[str, str | None]:
    import importlib.metadata

    names = ["numpy", "scipy", "qiskit", "quimb", "qiskit-quimb", "cotengra", "numba"]
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _blas_config() -> str | None:
    try:
        import numpy as np

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            np.__config__.show()
        return stream.getvalue().strip()
    except Exception as exc:  # pragma: no cover - depends on the installed NumPy build
        return f"unavailable: {type(exc).__name__}: {exc}"


def collect() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "cpu_model": _cpu_model(),
        "logical_cpus": os.cpu_count(),
        "available_cpus": _available_cpus(),
        "memory_bytes": _memory_bytes(),
        "environment_threads": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "BLIS_NUM_THREADS",
                "NUMBA_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
            )
        },
        "package_versions": _package_versions(),
        "numpy_blas_configuration": _blas_config(),
        "lscpu": _command_json(["lscpu", "--json"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Also write the JSON report to this path.")
    args = parser.parse_args()
    report = collect()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
