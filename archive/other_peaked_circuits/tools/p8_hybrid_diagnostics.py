#!/usr/bin/env python3
"""Answer-blind local prototype for P8 candidate and observable scoring.

The empirical marginals/correlations come from a classical sample file.  This
is deliberately a local stand-in for future IBM Z_i/Z_iZ_j measurements; it
must not be described as hardware evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def read_samples(path: Path) -> list[str]:
    rows = path.read_text().splitlines()
    header = rows[0].split("\t")
    column = "permuted" if "permuted" in header else header[0]
    idx = header.index(column)
    samples = [line.split("\t")[idx].strip() for line in rows[1:] if line.strip()]
    if not samples or any(len(x) != 40 or set(x) - {"0", "1"} for x in samples):
        raise ValueError("expected nonempty 40-bit P8 samples")
    return samples


def z_stats(samples: list[str]) -> tuple[list[float], dict[tuple[int, int], float]]:
    n = len(samples)
    z = [[1 if bit == "0" else -1 for bit in sample] for sample in samples]
    means = [sum(row[i] for row in z) / n for i in range(40)]
    corr = {(i, j): sum(row[i] * row[j] for row in z) / n
            for i in range(40) for j in range(i + 1, 40)}
    return means, corr


def score(candidate: str, means: list[float], corr: dict[tuple[int, int], float], pairs: list[tuple[int, int]]) -> tuple[float, float]:
    signs = [1 if bit == "0" else -1 for bit in candidate]
    linear = sum(signs[i] * means[i] for i in range(40))
    pair_term = sum(signs[i] * signs[j] * corr[i, j] for i, j in pairs)
    return linear, pair_term


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    samples = read_samples(args.samples)
    means, corr = z_stats(samples)
    pairs = sorted(corr, key=lambda p: (-abs(corr[p]), p))[:20]
    candidates = [
        "0010111110100001101010111000001111111011",  # prior MettleQ
        "0110100010111101110010011101101100011011",  # prior Helios trial
        "1001100010111101111101101011111010010011",  # prior CircuitPerm seed
        "1001100010111101101101110011111010010011",  # prior CircuitPerm seed
        "1001101010111101111101101011111010010001",  # prior CircuitPerm seed
        "1000100010111001111101001011111010010011",  # independent rerun
        "0101010001111100110101000111001001001000",  # D=8 TTN
    ]
    rows = []
    for candidate in candidates:
        linear, pair_term = score(candidate, means, corr, pairs)
        rows.append({"candidate": candidate, "linear_Z_score": linear,
                     "top20_pair_score": pair_term,
                     "combined_score_lambda_0.25": linear + 0.25 * pair_term,
                     "sample_exact_count": Counter(samples)[candidate]})
    rows.sort(key=lambda r: (-r["combined_score_lambda_0.25"], r["candidate"]))
    payload = {
        "schema": "p8-local-hybrid-diagnostics-v1",
        "answer_blind": True,
        "external_target_scored": False,
        "sample_source": str(args.samples),
        "sample_sha256": hashlib.sha256(args.samples.read_bytes()).hexdigest(),
        "shots": len(samples),
        "candidate_pool_frozen": True,
        "candidate_pool_sha256": hashlib.sha256("\n".join(sorted(candidates)).encode()).hexdigest(),
        "observable_proxy": "empirical classical samples; not IBM measurements",
        "top_abs_correlations": [{"i": i, "j": j, "zizj": corr[i, j]} for i, j in pairs],
        "uncertain_bits_by_abs_mean": sorted(range(40), key=lambda i: abs(means[i]))[:10],
        "z_means": means,
        "candidate_scores": rows,
        "hardware_gate": "Do not submit until reduced observable circuit is implemented and locally validated.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"status": "COMPLETE", "top_candidate": rows[0]["candidate"], "shots": len(samples), "uncertain_bits": payload["uncertain_bits_by_abs_mean"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
