"""Blind, zero-compute extraction statistics for completed P11 samples."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np


BITS = 98
BOOTSTRAP_REPLICATES = 2000
SUBSAMPLE_SIZES = (50, 100, 200, 400, 600, 800)


def parse_samples(path: Path, canonical_column: str = "permuted") -> list[str]:
    """Read and strictly validate a solver ``raw\tpermuted`` sample file."""
    rows = list(csv.DictReader(path.open(newline=""), delimiter="\t"))
    if not rows or not {"raw", "permuted"}.issubset(rows[0]):
        raise ValueError(f"{path}: expected raw/permuted TSV header")
    if canonical_column not in {"raw", "permuted"}:
        raise ValueError("canonical_column must be raw or permuted")
    values: list[str] = []
    for index, row in enumerate(rows, 1):
        value = row.get(canonical_column, "")
        if len(value) != BITS or set(value) - {"0", "1"}:
            raise ValueError(f"{path}: row {index} is not exactly {BITS} bits")
        raw = row.get("raw", "")
        permuted = row.get("permuted", "")
        if len(raw) != BITS or set(raw) - {"0", "1"}:
            raise ValueError(f"{path}: row {index} has malformed raw bits")
        if len(permuted) != BITS or set(permuted) - {"0", "1"}:
            raise ValueError(f"{path}: row {index} has malformed permuted bits")
        values.append(value)
    if len(values) != 1000:
        raise ValueError(f"{path}: expected 1000 samples, found {len(values)}")
    return values


def _bits(samples: list[str]) -> np.ndarray:
    return np.fromiter((int(bit) for sample in samples for bit in sample), dtype=np.uint8).reshape(
        len(samples), BITS
    )


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("trials must be positive")
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def hamming(a: str, b: str) -> int:
    if len(a) != len(b):
        raise ValueError("bitstrings must have equal length")
    return sum(x != y for x, y in zip(a, b))


def majority_candidate(samples: list[str]) -> tuple[str, list[bool]]:
    matrix = _bits(samples)
    ones = matrix.sum(axis=0)
    ties = (ones * 2 == len(samples)).tolist()
    return "".join("1" if count > len(samples) / 2 else "0" for count in ones), ties


def _quantiles(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=float)
    return {
        "q05": float(np.quantile(array, 0.05, method="linear")),
        "q25": float(np.quantile(array, 0.25, method="linear")),
        "q50": float(np.quantile(array, 0.50, method="linear")),
        "q75": float(np.quantile(array, 0.75, method="linear")),
        "q95": float(np.quantile(array, 0.95, method="linear")),
    }


def _pairwise_hamming(matrix: np.ndarray) -> dict[str, Any]:
    distances: list[np.ndarray] = []
    for start in range(len(matrix) - 1):
        distances.append(np.count_nonzero(matrix[start + 1 :] != matrix[start], axis=1))
    values = np.concatenate(distances).astype(np.int16) if distances else np.array([], dtype=np.int16)
    return {
        "pairs": int(values.size),
        "mean": float(values.mean()) if values.size else 0.0,
        "std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
        "quantiles": _quantiles(values.tolist()) if values.size else {},
    }


def _bootstrap(samples: list[str], candidate: str, rng: np.random.Generator) -> dict[str, Any]:
    matrix = _bits(samples)
    n = len(samples)
    sign_counts = np.zeros(BITS, dtype=np.int64)
    distances: list[int] = []
    candidates: Counter[str] = Counter()
    for _ in range(BOOTSTRAP_REPLICATES):
        draw = matrix[rng.integers(0, n, size=n)]
        ones = draw.sum(axis=0)
        boot = "".join("1" if count > n / 2 else "0" for count in ones)
        candidates[boot] += 1
        sign_counts += (np.asarray(list(boot), dtype="U1") == np.asarray(list(candidate))).astype(int)
        distances.append(hamming(boot, candidate))
    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "majority_sign_stability": (sign_counts / BOOTSTRAP_REPLICATES).tolist(),
        "candidate_hamming_to_full_majority": {
            "mean": float(np.mean(distances)),
            "std": float(np.std(distances, ddof=1)),
            "quantiles": _quantiles(distances),
        },
        "whole_candidate_top10": candidates.most_common(10),
    }


def _subsample_convergence(samples: list[str], candidate: str, rng: np.random.Generator) -> dict[str, Any]:
    matrix = _bits(samples)
    result: dict[str, Any] = {}
    for size in SUBSAMPLE_SIZES:
        distances: list[int] = []
        agreements: list[float] = []
        for _ in range(BOOTSTRAP_REPLICATES):
            draw = matrix[rng.choice(len(matrix), size=size, replace=False)]
            ones = draw.sum(axis=0)
            sub = "".join("1" if count > size / 2 else "0" for count in ones)
            distances.append(hamming(sub, candidate))
            agreements.append(1 - distances[-1] / BITS)
        result[str(size)] = {
            "replicates": BOOTSTRAP_REPLICATES,
            "mean_hamming_to_full_majority": float(np.mean(distances)),
            "hamming_quantiles": _quantiles(distances),
            "mean_bit_agreement_to_full_majority": float(np.mean(agreements)),
        }
    return result


def _run_analysis(samples: list[str], rng: np.random.Generator) -> dict[str, Any]:
    matrix = _bits(samples)
    n = len(samples)
    ones = matrix.sum(axis=0)
    candidate, ties = majority_candidate(samples)
    bits: list[dict[str, Any]] = []
    for index, count in enumerate(ones):
        p = float(count / n)
        interval = wilson_interval(int(count), n)
        entropy = 0.0 if p in (0.0, 1.0) else -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
        bits.append({
            "index": index,
            "p1": p,
            "p0": 1 - p,
            "bias": abs(p - 0.5),
            "entropy_bits": entropy,
            "majority": candidate[index],
            "tie_uncertain": ties[index],
            "wilson95_p1_low": interval[0],
            "wilson95_p1_high": interval[1],
        })
    bootstrap = _bootstrap(samples, candidate, rng)
    return {
        "shots": n,
        "bits": BITS,
        "majority_candidate": candidate,
        "tie_positions": [i for i, tie in enumerate(ties) if tie],
        "per_bit": bits,
        "within_run_pairwise_hamming": _pairwise_hamming(matrix),
        "bootstrap": bootstrap,
        "subsample_convergence": _subsample_convergence(samples, candidate, rng),
    }


def _held_out(samples: list[str], candidate: str, rng: np.random.Generator) -> dict[str, Any]:
    values = np.asarray([hamming(sample, candidate) for sample in samples], dtype=float)
    means = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
    for i in range(BOOTSTRAP_REPLICATES):
        means[i] = values[rng.integers(0, len(values), size=len(values))].mean()
    return {
        "candidate": candidate,
        "samples": len(values),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "std": float(values.std(ddof=1)),
        "quantiles": _quantiles(values.tolist()),
        "null_mean": 49.0,
        "difference_from_null": float(values.mean() - 49.0),
        "effect_size_vs_null_sd": float((values.mean() - 49.0) / math.sqrt(98 * 0.25)),
        "bootstrap_mean_ci95": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))],
        "bootstrap_mean_upper_below_48": bool(np.quantile(means, 0.975) < 48),
        "bootstrap_mean_upper_below_49": bool(np.quantile(means, 0.975) < 49),
    }


def analyze_samples(run5: Path, run4: Path, outdir: Path) -> dict[str, Any]:
    """Run preregistered Phase A analysis and write all required artifacts."""
    outdir.mkdir(parents=True, exist_ok=True)
    samples5 = parse_samples(run5)
    samples4 = parse_samples(run4)
    rng = np.random.Generator(np.random.PCG64(20260827))
    rng_sub = np.random.Generator(np.random.PCG64(20260828))
    result5 = _run_analysis(samples5, rng)
    result4 = _run_analysis(samples4, rng_sub)
    candidate5 = result5["majority_candidate"]
    candidate4 = result4["majority_candidate"]
    held_5_to_4 = _held_out(samples4, candidate5, rng)
    held_4_to_5 = _held_out(samples5, candidate4, rng_sub)
    per_bit: list[dict[str, Any]] = []
    for a, b in zip(result5["per_bit"], result4["per_bit"]):
        per_bit.append({
            "index": a["index"], "p5": a["p1"], "p4": b["p1"],
            "majority5": a["majority"], "majority4": b["majority"],
            "agreement": a["majority"] == b["majority"],
            "bias5": a["bias"], "bias4": b["bias"],
            "bootstrap_stability5": result5["bootstrap"]["majority_sign_stability"][a["index"]],
            "bootstrap_stability4": result4["bootstrap"]["majority_sign_stability"][b["index"]],
            "confidence_interval5": [a["wilson95_p1_low"], a["wilson95_p1_high"]],
            "confidence_interval4": [b["wilson95_p1_low"], b["wilson95_p1_high"]],
        })
    agreement = sum(row["agreement"] for row in per_bit)
    stable = sum(row["bootstrap_stability5"] >= 0.90 and row["bootstrap_stability4"] >= 0.90 for row in per_bit)
    cross = {
        "candidate5": candidate5,
        "candidate4": candidate4,
        "candidate_hamming": hamming(candidate5, candidate4),
        "majority_sign_agreement": agreement,
        "stable_bits_both_ge_0_90": stable,
        "held_out_5e3_candidate_on_4e3_samples": held_5_to_4,
        "held_out_4e3_candidate_on_5e3_samples": held_4_to_5,
    }
    if (cross["candidate_hamming"] <= 12 and agreement >= 80 and
            held_5_to_4["bootstrap_mean_upper_below_48"] and
            held_4_to_5["bootstrap_mean_upper_below_48"] and stable >= 60):
        grade = "STRONG_CROSS_RUN_SIGNAL"
    elif (cross["candidate_hamming"] <= 20 and agreement >= 70 and
          held_5_to_4["bootstrap_mean_upper_below_49"] and
          held_4_to_5["bootstrap_mean_upper_below_49"]):
        grade = "MODERATE_CROSS_RUN_SIGNAL"
    else:
        grade = "NO_REPRODUCIBLE_SIGNAL"
    analysis = {
        "protocol": "docs/P11_EXTRACTION_PROTOCOL.md",
        "inputs": {"5e-3": str(run5), "4e-3": str(run4), "canonical_column": "permuted"},
        "blindness": {"expected_bitstring": "", "external_target_used": False, "external_verifier_used": False},
        "runs": {"5e-3": result5, "4e-3": result4},
        "cross_run": cross,
        "decision_grade": grade,
    }
    (outdir / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
    (outdir / "cross_run.json").write_text(json.dumps(cross, indent=2) + "\n")
    (outdir / "bootstrap.json").write_text(json.dumps({"5e-3": result5["bootstrap"], "4e-3": result4["bootstrap"]}, indent=2) + "\n")
    with (outdir / "per_bit.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_bit[0]))
        writer.writeheader(); writer.writerows(per_bit)
    hashes = []
    for path in sorted(outdir.iterdir()):
        if path.name == "SHA256SUMS" or not path.is_file():
            continue
        hashes.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (outdir / "SHA256SUMS").write_text("\n".join(hashes) + "\n")
    return analysis
