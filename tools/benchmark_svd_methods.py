#!/usr/bin/env python3
"""Benchmark quimb's deterministic and randomized truncated SVD on P9-like shapes."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()

    from quimb.tensor import decomp

    shapes = ((128, 128, 64), (256, 256, 128), (512, 256, 128), (1024, 512, 256))
    rows = []
    for shape_index, (nrow, ncol, max_bond) in enumerate(shapes):
        rng = np.random.default_rng(123 + shape_index)
        matrix = rng.standard_normal((nrow, ncol)) + 1j * rng.standard_normal((nrow, ncol))
        reference = np.linalg.norm(matrix)
        for method in ("svd", "rsvd"):
            times = []
            errors = []
            for _ in range(args.repetitions):
                started = time.perf_counter()
                fn = decomp.svd_truncated if method == "svd" else decomp.rsvd
                left, _singular, right = fn(
                    matrix,
                    cutoff=0.0,
                    max_bond=max_bond,
                    absorb=0,
                )
                elapsed = time.perf_counter() - started
                # Quimb absorbs singular values into one factor for these
                # truncated decompositions and returns ``singular=None``.
                reconstructed = left @ right
                times.append(elapsed)
                errors.append(float(np.linalg.norm(matrix - reconstructed) / reference))
            rows.append(
                {
                    "shape": f"{nrow}x{ncol}",
                    "max_bond": max_bond,
                    "method": method,
                    "repetitions": args.repetitions,
                    "median_time_s": float(np.median(times)),
                    "min_time_s": float(min(times)),
                    "max_time_s": float(max(times)),
                    "max_relative_reconstruction_error": max(errors),
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} benchmark rows to {args.output}")


if __name__ == "__main__":
    main()
