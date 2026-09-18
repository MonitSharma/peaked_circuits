#!/usr/bin/env python3
from pathlib import Path

from p12_recovery.cli import compile_command

if __name__ == "__main__":
    compile_command(Path("configs/compilation.yaml"))
