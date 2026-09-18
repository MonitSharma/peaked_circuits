#!/usr/bin/env python3
from __future__ import annotations

import argparse

from p12_recovery.bluequbit.particle_sv import run_particle_circuit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm")
    ap.add_argument("out")
    ap.add_argument("--particles", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--max-seconds", type=float, default=120.0)
    args = ap.parse_args()
    run_particle_circuit(args.qasm, args.particles, args.seed, args.out, max_seconds=args.max_seconds)


if __name__ == "__main__":
    main()
