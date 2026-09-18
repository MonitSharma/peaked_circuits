#!/usr/bin/env python3
"""Portable Linux/Mac hardware, NUMA, BLAS, and environment discovery."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def run(*command: str) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"<unavailable: {type(exc).__name__}: {exc}>"


def cpu_topology() -> dict[str, object]:
    root = Path("/sys/devices/system/cpu")
    packages: dict[tuple[str, str], list[int]] = {}
    for path in root.glob("cpu[0-9]*"):
        try:
            cpu = int(path.name[3:])
            package = (path / "topology/physical_package_id").read_text().strip()
            core = (path / "topology/core_id").read_text().strip()
        except (OSError, ValueError):
            continue
        packages.setdefault((package, core), []).append(cpu)
    physical = sorted(min(cpus) for cpus in packages.values())
    siblings = sorted(cpu for cpus in packages.values() for cpu in cpus if cpu not in physical)
    numa: dict[str, list[int]] = {}
    for path in Path("/sys/devices/system/node").glob("node[0-9]*"):
        try:
            cpulist = (path / "cpulist").read_text().strip()
        except OSError:
            continue
        numa[path.name] = expand_cpu_list(cpulist)
    return {"physical_cpu_count": len(physical), "physical_cpu_ids": physical, "smt_sibling_ids": siblings, "socket_core_pairs": len(packages), "numa_cpu_lists": numa}


def expand_cpu_list(value: str) -> list[int]:
    result: list[int] = []
    for part in value.split(","):
        if "-" in part:
            start, end = (int(x) for x in part.split("-", 1))
            result.extend(range(start, end + 1))
        elif part:
            result.append(int(part))
    return result


def blas_info() -> dict[str, object]:
    try:
        import numpy as np

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            np.show_config()
        config = stream.getvalue()
    except Exception as exc:
        config = f"<unavailable: {type(exc).__name__}: {exc}>"
    try:
        from threadpoolctl import threadpool_info

        pools = threadpool_info()
    except Exception as exc:
        pools = [{"error": f"{type(exc).__name__}: {exc}"}]
    return {"numpy_show_config": config, "threadpoolctl": pools}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("results/hpc_preflight"))
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    topology = cpu_topology()
    hardware = {"uname": run("uname", "-a"), "lscpu": run("lscpu"), "numactl_H": run("numactl", "-H"), "free": run("free", "-h"), "df": run("df", "-h", str(args.repo_root)), "ulimit": run("bash", "-lc", "ulimit -a"), "platform": platform.platform(), "cpu": topology, "memory_bytes": os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else None}
    environment = {"python": sys.version, "executable": sys.executable, "git_head": run("git", "-C", str(args.repo_root), "rev-parse", "HEAD"), "git_status": run("git", "-C", str(args.repo_root), "status", "--short"), "packages": {}}
    for name in ("numpy", "scipy", "quimb", "cotengra", "numba", "psutil", "threadpoolctl", "pandas"):
        try:
            import importlib.metadata as metadata

            environment["packages"][name] = metadata.version(name)
        except Exception as exc:
            environment["packages"][name] = f"<unavailable: {type(exc).__name__}>"
    (out / "HARDWARE.json").write_text(json.dumps(hardware, indent=2, sort_keys=True) + "\n")
    (out / "ENVIRONMENT.json").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n")
    (out / "blas.json").write_text(json.dumps(blas_info(), indent=2, sort_keys=True) + "\n")
    (out / "PREFLIGHT.md").write_text("# HPC preflight\n\n```text\n" + json.dumps(hardware, indent=2, sort_keys=True) + "\n```\n\nEnvironment is recorded in `ENVIRONMENT.json`; BLAS details are in `blas.json`.\n")
    print(json.dumps({"output_dir": str(out), "physical_cpu_count": topology["physical_cpu_count"], "numa_nodes": len(topology["numa_cpu_lists"])}, sort_keys=True))


if __name__ == "__main__":
    main()
