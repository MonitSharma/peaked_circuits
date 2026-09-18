"""Answer-blind ensemble reliability and bounded completion utilities.

This module deliberately works on frozen approximation outputs only.  It has no
interface for an expected answer, overlap score, portal feedback, or evaluation
oracle.  Approximation rungs from one family are retained as evidence but are
never counted as independent families.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import math
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any


def read_bitstrings(path: str | Path, *, column: str = "permuted") -> list[str]:
    path = Path(path)
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or column not in rows[0]:
        raise ValueError(f"{path}: missing TSV column {column!r}")
    values = [str(row[column]).strip() for row in rows]
    width = len(values[0])
    if width == 0 or any(len(value) != width or set(value) - {"0", "1"} for value in values):
        raise ValueError(f"{path}: malformed bitstrings")
    return values


def summarize_samples(
    samples: Sequence[str], *, method_family: str, run_id: str, source: str
) -> dict[str, Any]:
    if not samples:
        raise ValueError("samples cannot be empty")
    width = len(samples[0])
    if any(len(value) != width or set(value) - {"0", "1"} for value in samples):
        raise ValueError("samples must be equal-width binary strings")
    counts = [sum(value[index] == "1" for value in samples) for index in range(width)]
    probabilities = [count / len(samples) for count in counts]
    candidate = "".join("1" if value > 0.5 else "0" for value in probabilities)
    return {
        "run_id": run_id,
        "method_family": method_family,
        "source": str(source),
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "shots": len(samples),
        "bits": width,
        "unique_strings": len(set(samples)),
        "candidate": candidate,
        "p1": probabilities,
        "margins": [abs(value - 0.5) * 2.0 for value in probabilities],
        "answer_blind": True,
    }


def classify_bit(*, agreement_fraction: float, median_margin: float, family_count: int) -> str:
    """Conservative classification; one family cannot create LOCKED bits."""
    if family_count >= 2 and agreement_fraction >= 0.90 and median_margin >= 0.20:
        return "LOCKED"
    if agreement_fraction >= 0.70 and median_margin >= 0.10:
        return "LIKELY"
    if agreement_fraction < 0.50:
        return "CONFLICTED"
    return "UNCERTAIN"


def reliability(runs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(runs)
    if not rows:
        raise ValueError("at least one run is required")
    widths = {int(row["bits"]) for row in rows}
    if len(widths) != 1:
        raise ValueError("all ensemble runs must have the same bit width")
    width = widths.pop()
    families = sorted({str(row.get("method_family", "unknown")) for row in rows})
    bits = []
    for index in range(width):
        predictions = [str(row["candidate"])[index] for row in rows]
        margins = [float(row["margins"][index]) for row in rows]
        counts = Counter(predictions)
        predicted, votes = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
        bits.append({
            "index": index,
            "predicted_bit": predicted,
            "agreement_fraction": votes / len(predictions),
            "median_margin": sorted(margins)[len(margins) // 2],
            "margin_iqr": _iqr(margins),
            "method_family_count": len({str(row.get("method_family", "unknown")) for row in rows}),
            "classification": classify_bit(
                agreement_fraction=votes / len(predictions),
                median_margin=sorted(margins)[len(margins) // 2],
                family_count=len(families),
            ),
        })
    return {
        "schema": "p12-p5-answer-blind-reliability-v1",
        "answer_blind": True,
        "run_count": len(rows),
        "method_families": families,
        "bits": bits,
        "counts": Counter(bit["classification"] for bit in bits),
        "candidate": "".join(bit["predicted_bit"] for bit in bits),
    }


def _iqr(values: Sequence[float]) -> float:
    ordered = sorted(values)
    if len(ordered) < 2:
        return 0.0
    return float(ordered[(3 * len(ordered)) // 4] - ordered[len(ordered) // 4])


def enumerate_completions(
    fixed: str,
    uncertain_indices: Sequence[int],
    score: Callable[[str], float],
    *,
    max_completions: int = 1_048_576,
) -> list[dict[str, Any]]:
    """Enumerate a bounded joint completion set and rank it by an answer-blind score."""
    if set(fixed) - {"0", "1", "?"}:
        raise ValueError("fixed must contain only 0, 1, or ?")
    indices = tuple(uncertain_indices)
    if len(set(indices)) != len(indices) or any(i < 0 or i >= len(fixed) for i in indices):
        raise ValueError("uncertain_indices must be unique and in range")
    if any(fixed[i] != "?" for i in indices):
        raise ValueError("uncertain indices must point to '?' positions")
    total = 1 << len(indices)
    if total > max_completions:
        raise ValueError(f"completion count {total} exceeds bound {max_completions}")
    ranked = []
    for assignment in itertools.product("01", repeat=len(indices)):
        chars = list(fixed)
        for index, bit in zip(indices, assignment, strict=True):
            chars[index] = bit
        candidate = "".join(chars)
        value = float(score(candidate))
        if not math.isfinite(value):
            raise ValueError("completion score must be finite")
        ranked.append({"candidate": candidate, "score": value})
    ranked.sort(key=lambda row: (-row["score"], row["candidate"]))
    return ranked
