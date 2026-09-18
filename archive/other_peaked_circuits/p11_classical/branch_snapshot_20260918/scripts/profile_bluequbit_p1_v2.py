#!/usr/bin/env python3
"""Build the blind P1 v2 structural/profile artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from p12_recovery.bluequbit.profile import write_profile_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    write_profile_bundle(args.qasm, args.outdir)


if __name__ == "__main__":
    main()
