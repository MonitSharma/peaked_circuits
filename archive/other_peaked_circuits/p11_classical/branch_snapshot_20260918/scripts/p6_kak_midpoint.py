"""Run a bounded, answer-blind midpoint test over extracted KAK blocks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def midpoint_score(blocks: list[dict], midpoint: int, window: int, seed: int,
                   controls: int) -> dict:
    left = sorted((b for b in blocks if b["end_event"] < midpoint),
                  key=lambda b: b["start_event"])
    right = sorted((b for b in blocks if b["start_event"] >= midpoint),
                   key=lambda b: b["start_event"])
    left_positions = np.asarray([(b["start_event"] + b["end_event"]) / 2 for b in left])
    right_positions = np.asarray([(b["start_event"] + b["end_event"]) / 2 for b in right])
    left_signatures = np.asarray([b["weyl"] for b in left])
    right_signatures = np.asarray([b["weyl"] for b in right])
    paired_indices = [
        np.flatnonzero(np.abs(right_positions - (2 * midpoint - position)) <= window)
        for position in left_positions
    ]

    def score(signatures: np.ndarray) -> float:
        distances = []
        for index, choices in enumerate(paired_indices):
            if len(choices):
                distances.append(np.linalg.norm(signatures[choices] - left_signatures[index], axis=1).min())
        return float(np.mean(distances))

    observed = score(right_signatures)
    rng = np.random.default_rng(seed)
    null = [score(right_signatures[rng.permutation(len(right_signatures))]) for _ in range(controls)]
    return {
        "midpoint": midpoint,
        "window": window,
        "left_blocks": len(left),
        "right_blocks": len(right),
        "observed_mean_nearest_weyl_distance": observed,
        "null_mean": float(np.mean(null)),
        "null_sd": float(np.std(null)),
        "z_improvement": (float(np.mean(null)) - observed) / float(np.std(null)) if np.std(null) else None,
        "exact_nearest_matches": int(sum(
            np.min(np.linalg.norm(right_signatures[choices] - left_signatures[index], axis=1)) <= 1e-6
            for index, choices in enumerate(paired_indices) if len(choices)
        )),
        "controls": controls,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("blocks", type=Path)
    parser.add_argument("--midpoint", type=int, default=5243)
    parser.add_argument("--window", type=int, default=500)
    parser.add_argument("--controls", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = midpoint_score(json.loads(args.blocks.read_text())["blocks"], args.midpoint,
                            args.window, 123, args.controls)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
