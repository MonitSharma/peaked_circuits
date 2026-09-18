"""Run provenance for the sparse campaign."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np


def git_info(path: str | Path) -> dict:
    path = str(path)
    def run(*args):
        try:
            return subprocess.check_output(["git", "-C", path, *args], text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment() -> dict:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
    }
