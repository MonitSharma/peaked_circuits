#!/usr/bin/env python3
from pathlib import Path

from p12_recovery.cli import synthetic

if __name__ == "__main__":
    synthetic(Path("configs/synthetic.yaml"), False)
