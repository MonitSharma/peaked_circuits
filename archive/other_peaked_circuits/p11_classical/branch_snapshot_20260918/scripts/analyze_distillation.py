#!/usr/bin/env python3
"""Answer-blind bitwise distillation audit for peaked-circuit samples."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np


def read_samples(path: Path, column: str = "permuted") -> list[str]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or column not in rows[0]:
        raise ValueError(f"{path}: missing TSV column {column!r}")
    values = [row[column] for row in rows]
    nbits = len(values[0])
    if nbits == 0 or any(len(value) != nbits or set(value) - {"0", "1"} for value in values):
        raise ValueError(f"{path}: malformed bitstrings")
    return values


def majority(samples: list[str]) -> str:
    matrix = np.asarray([[int(bit) for bit in sample] for sample in samples], dtype=np.uint8)
    return "".join("1" if count > len(samples) / 2 else "0" for count in matrix.sum(axis=0))


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b, strict=True))


def bootstrap(samples: list[str], candidate: str, rng: np.random.Generator, repeats: int = 2000) -> dict:
    matrix = np.asarray([[int(bit) for bit in sample] for sample in samples], dtype=np.uint8)
    candidates = Counter()
    bit_stability = np.zeros(matrix.shape[1], dtype=np.int64)
    distances: list[int] = []
    for _ in range(repeats):
        draw = matrix[rng.integers(0, len(matrix), size=len(matrix))]
        value = "".join("1" if count > len(samples) / 2 else "0" for count in draw.sum(axis=0))
        candidates[value] += 1
        bit_stability += np.fromiter((a == b for a, b in zip(value, candidate, strict=True)), dtype=np.int64)
        distances.append(hamming(value, candidate))
    return {
        "replicates": repeats,
        "bit_sign_stability": (bit_stability / repeats).tolist(),
        "candidate_hamming_quantiles": {str(q): float(np.quantile(distances, q)) for q in (0.05, 0.5, 0.95)},
        "whole_candidate_top10": candidates.most_common(10),
    }


def analyze(path: Path, outdir: Path, column: str, seed: int) -> dict:
    samples = read_samples(path, column)
    candidate = majority(samples)
    matrix = np.asarray([[int(bit) for bit in sample] for sample in samples], dtype=np.uint8)
    counts = matrix.sum(axis=0)
    n = len(samples)
    rng = np.random.default_rng(seed)
    per_bit = []
    for index, count in enumerate(counts):
        p = float(count / n)
        z = 1.959963984540054
        denom = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denom
        half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
        per_bit.append({"index": index, "p1": p, "margin": abs(p - 0.5), "majority": candidate[index],
                        "wilson95": [max(0.0, center - half), min(1.0, center + half)]})
    convergence = {}
    for size in (100, 200, 400, 600, 800, n):
        if size > n:
            continue
        draw = matrix[:size]
        sub = "".join("1" if count > size / 2 else "0" for count in draw.sum(axis=0))
        convergence[str(size)] = {"candidate": sub, "hamming_to_full": hamming(sub, candidate)}
    result = {
        "schema": "peaked-circuit-distillation-audit-v1",
        "input": str(path),
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "column": column,
        "shots": n,
        "bits": len(candidate),
        "unique_strings": len(set(samples)),
        "modal_frequency": Counter(samples).most_common(1)[0][1],
        "majority_candidate": candidate,
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "per_bit": per_bit,
        "bootstrap": bootstrap(samples, candidate, rng),
        "subsample_convergence": convergence,
        "gate": {
            "candidate": candidate,
            "split_half_hamming": hamming(majority(samples[: n // 2]), majority(samples[n // 2:])),
            "bootstrap_bits_ge_0_90": sum(v >= 0.90 for v in bootstrap(samples, candidate, np.random.default_rng(seed + 1))["bit_sign_stability"]),
        },
    }
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("samples", type=Path)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--column", choices=("raw", "permuted"), default="permuted")
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()
    result = analyze(args.samples, args.outdir, args.column, args.seed)
    print(json.dumps({k: result[k] for k in ("input", "bits", "shots", "unique_strings", "modal_frequency", "majority_candidate", "gate")}, indent=2))


if __name__ == "__main__":
    main()
