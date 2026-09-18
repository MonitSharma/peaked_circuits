#!/usr/bin/env python3
"""Run one bounded, answer-blind P1 sparse-state trajectory."""

from __future__ import annotations

import argparse

from p12_recovery.bluequbit.sparse_sv import run_sparse_circuit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm")
    parser.add_argument("outdir")
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--dtype", choices=("complex64", "complex128"), default="complex128")
    parser.add_argument("--max-rss-gib", type=float, default=30.0)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--schedule", choices=("original", "cz_first"), default="original")
    parser.add_argument("--p-frac", type=float, default=1.0)
    args = parser.parse_args()
    run_sparse_circuit(args.qasm, args.top_k, args.outdir, dtype=args.dtype, max_rss_bytes=int(args.max_rss_gib * 1024**3), max_seconds=args.max_seconds, schedule=args.schedule, p_frac=args.p_frac)


if __name__ == "__main__":
    main()
