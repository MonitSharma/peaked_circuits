#!/usr/bin/env python3
"""Generate the compact figures used in the P9 tracker submission draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _short(bitstring: str) -> str:
    return f"{bitstring[:8]}…{bitstring[-8:]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary = _load(args.summary)
    comparison = _load(args.comparison)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    counts = summary["counts"]
    predicted = summary["predicted_bitstring"]
    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:10]
    top.reverse()
    labels = [
        f"#{index} {_short(bitstring)}"
        for index, (bitstring, _) in enumerate(reversed(top), start=1)
    ][::-1]
    values = [count for _, count in top]
    colors = ["#c0392b" if bitstring == predicted else "#4f81bd" for bitstring, _ in top]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels, values, color=colors)
    ax.set_xlabel("Count out of 1,000 samples")
    ax.set_title("P9 MettleQ samples — seed 123, exact oracle recovered")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values, strict=True):
        ax.text(value + 0.8, bar.get_y() + bar.get_height() / 2, str(value), va="center")
    fig.tight_layout()
    fig.savefig(args.output_dir / "p9_mettleq_samples.png", dpi=220)
    plt.close(fig)

    runs_by_id = {run["id"]: run for run in comparison["runs"]}
    upstream = runs_by_id["upstream_seed123_d512_c6e4_threads2"]
    submitted = runs_by_id.get(
        "clean_commit_e53a61a_complex64_seed123",
        runs_by_id["precision_complex64_full_p9_seed123_d512_c6e4_threads2"],
    )
    runs = [upstream, submitted]
    names = ["Upstream\nMPO + unswapping", "MettleQ\ncomplex64"]
    times = [run["total_time_s"] for run in runs]
    colors = ["#7f8c8d", "#167d8d"]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, times, color=colors, width=0.58)
    ax.set_ylabel("Wall time (seconds)")
    ax.set_title("P9 seed-123 runtime on the same M3 Pro")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, times, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(times) * 0.02,
                f"{value:.1f} s", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(args.output_dir / "p9_runtime_comparison.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
