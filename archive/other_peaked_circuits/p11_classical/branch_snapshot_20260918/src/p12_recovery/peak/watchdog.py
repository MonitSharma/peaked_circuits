"""Portable, testable process-tree resource policy."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class WatchdogLimits:
    rss_hard_bytes: int = 24 * 1024**3
    wall_seconds: float = 7 * 3600
    swap_growth_bytes: int = 2 * 1024**3
    child_process_limit: int = 8


def tree_rss_bytes(root_pid: int) -> int:
    try:
        rows = subprocess.check_output(["ps", "-Ao", "pid=,ppid=,rss="], text=True).splitlines()
    except (OSError, subprocess.CalledProcessError):
        return 0
    rss, children = {}, {}
    for row in rows:
        parts = row.split()
        if len(parts) != 3:
            continue
        pid, ppid, kb = map(int, parts)
        rss[pid] = kb * 1024
        children.setdefault(ppid, []).append(pid)
    todo, seen = [root_pid], set()
    total = 0
    while todo:
        pid = todo.pop()
        if pid in seen:
            continue
        seen.add(pid)
        total += rss.get(pid, 0)
        todo.extend(children.get(pid, ()))
    return total


def tree_process_ids(root_pid: int) -> set[int]:
    try:
        rows = subprocess.check_output(["ps", "-Ao", "pid=,ppid="], text=True).splitlines()
    except (OSError, subprocess.CalledProcessError):
        return {root_pid}
    children: dict[int, list[int]] = {}
    for row in rows:
        parts = row.split()
        if len(parts) == 2:
            pid, ppid = map(int, parts)
            children.setdefault(ppid, []).append(pid)
    todo, seen = [root_pid], set()
    while todo:
        pid = todo.pop()
        if pid in seen:
            continue
        seen.add(pid)
        todo.extend(children.get(pid, ()))
    return seen


def child_process_count(root_pid: int) -> int:
    return max(0, len(tree_process_ids(root_pid)) - 1)


def swap_used_bytes() -> int | None:
    try:
        text = subprocess.check_output(["sysctl", "-n", "vm.swapusage"], text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"used\s*=\s*([0-9.]+)([KMGTP])", text)
    if not match:
        return None
    scale = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    return int(float(match.group(1)) * scale[match.group(2)])


def memory_pressure_snapshot() -> str | None:
    try:
        return subprocess.check_output(["memory_pressure", "-Q"], text=True, stderr=subprocess.STDOUT, timeout=2).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def terminate_process_tree(process: subprocess.Popen, *, grace_seconds: float = 5.0) -> str:
    if process.poll() is not None:
        return "already_exited"
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        process.terminate()
    deadline = time.monotonic() + grace_seconds
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if process.poll() is None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            process.kill()
        return "sigkill_after_sigterm"
    return "sigterm"
