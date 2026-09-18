#!/usr/bin/env python3
"""Build compact, reproducible P9 benchmark tables and plots."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any


def _classification(summary: dict[str, Any], manifest: dict[str, Any]) -> str:
    if manifest.get("status") == "numerically_unstable":
        return "numerically_unstable"
    if manifest.get("status", "completed") != "completed":
        return "failed_or_timed_out"
    if manifest.get("returncode") not in (None, 0):
        return "failed_or_timed_out"
    if summary.get("matches_expected_bitstring") is True:
        return "exact_and_faster" if summary.get("total_time_s", float("inf")) < 734 else "exact_but_not_faster"
    if summary.get("matches_expected_bitstring") is False:
        return "incorrect_oracle"
    return "failed_or_timed_out"


def _run_rows(results_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs: list[dict[str, Any]] = []
    dynamics: list[dict[str, Any]] = []
    for manifest_path in sorted(results_root.glob("*/manifest.json")):
        run_dir = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            summary = {}
        else:
            summary = json.loads(summary_path.read_text())
        options = manifest.get("options", {})
        diagnostics = summary.get("diagnostics", {})
        safe_svd = diagnostics.get("quimb_safe_svd", {})
        threads = manifest.get("thread_environment", {})
        runs.append(
            {
                "run": run_dir.name,
                "classification": _classification(summary, manifest),
                "status": manifest.get("status", "completed"),
                "termination_reason": manifest.get("termination_reason"),
                "returncode": manifest.get("returncode"),
                "wall_time_s": manifest.get("wall_time_s"),
                "total_time_s": summary.get("total_time_s"),
                "compression_time_s": summary.get("compression_time_s"),
                "matches_expected_bitstring": summary.get("matches_expected_bitstring"),
                "predicted_bitstring": summary.get("predicted_bitstring"),
                "max_bond": options.get("max_bond"),
                "cutoff": options.get("cutoff"),
                "compression_method": options.get("compression_method", "svd"),
                "dtype": options.get("dtype", "complex128"),
                "seed": options.get("seed"),
                "python": manifest.get("environment", {}).get("python"),
                "numpy": manifest.get("environment", {}).get("numpy"),
                "scipy": manifest.get("environment", {}).get("scipy"),
                "quimb": manifest.get("environment", {}).get("quimb"),
                "qiskit": manifest.get("environment", {}).get("qiskit"),
                "mettleq_git_commit": manifest.get("mettleq_git_commit"),
                "mettleq_git_dirty": manifest.get("mettleq_git_dirty"),
                "veclib_threads": threads.get("VECLIB_MAXIMUM_THREADS"),
                "omp_threads": threads.get("OMP_NUM_THREADS"),
                "svd_isolation_min_elements": threads.get("METTLEQ_MPO_SVD_ISOLATION_MIN_ELEMENTS"),
                "peak_max_bond": diagnostics.get("peak_max_bond"),
                "peak_total_elements": diagnostics.get("peak_total_elements"),
                "work_gates_consumed": diagnostics.get("work_gates_consumed"),
                "total_work_gates": diagnostics.get("total_work_gates"),
                "native_svd_calls": safe_svd.get("native_in_process_calls"),
                "isolated_svd_calls": safe_svd.get("isolated_scipy_gesvd_calls"),
                "isolated_svd_failures": safe_svd.get("isolated_scipy_gesvd_failures"),
                "peak_rss_bytes": manifest.get("peak_rss_bytes"),
            }
        )
        stats_path = run_dir / "stats.json"
        if stats_path.exists():
            for row in json.loads(stats_path.read_text()):
                item = {"run": run_dir.name, **row}
                dynamics.append(item)
    return runs, dynamics


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot(results_root: Path, dynamics: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    for run in sorted({row["run"] for row in dynamics}):
        rows = [row for row in dynamics if row["run"] == run and row.get("time") is not None]
        if not rows:
            continue
        x = [float(row["time"]) for row in rows]
        y = [float(row.get("total_elems", 0)) for row in rows]
        bond = [float(row.get("max_bond", 0)) for row in rows]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(x, y, label="MPO elements")
        ax.set_xlabel("elapsed time (s)")
        ax.set_ylabel("total MPO elements")
        ax.set_title(run)
        ax.grid(alpha=0.25)
        ax2 = ax.twinx()
        ax2.plot(x, bond, color="tab:orange", alpha=0.8, label="max bond")
        ax2.set_ylabel("maximum bond")
        fig.tight_layout()
        fig.savefig(results_root / f"{run}_contraction_dynamics.png", dpi=140)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_root", type=Path)
    args = parser.parse_args()
    runs, dynamics = _run_rows(args.results_root)
    _write_csv(args.results_root / "summary.csv", runs)
    _write_csv(args.results_root / "contraction_dynamics.csv", dynamics)
    _write_csv(args.results_root / "configuration_by_time.csv", runs)
    _write_csv(
        args.results_root / "failure_summary.csv",
        [
            {
                "run": row["run"],
                "classification": row["classification"],
                "status": row["status"],
                "termination_reason": row["termination_reason"],
                "returncode": row["returncode"],
                "wall_time_s": row["wall_time_s"],
                "work_gates_consumed": row["work_gates_consumed"],
                "total_work_gates": row["total_work_gates"],
                "peak_rss_bytes": row["peak_rss_bytes"],
            }
            for row in runs
            if row["classification"] not in {"exact_and_faster", "exact_but_not_faster"}
        ],
    )
    _write_csv(
        args.results_root / "peak_memory.csv",
        [
            {
                "run": row["run"],
                "classification": row["classification"],
                "peak_rss_bytes": row["peak_rss_bytes"],
                "peak_rss_gib": (
                    float(row["peak_rss_bytes"]) / (1024**3)
                    if row.get("peak_rss_bytes")
                    else None
                ),
                "max_bond": row["max_bond"],
                "cutoff": row["cutoff"],
                "seed": row["seed"],
            }
            for row in runs
        ],
    )
    finalist_seeds = {123, 7, 42, 31415, 271828}
    finalist_runs = [
        row
        for row in runs
        if row.get("seed") in finalist_seeds
        and row.get("max_bond") == 512
        and row.get("cutoff") == 0.0006
        and row.get("svd_isolation_min_elements") == 131072
        and row.get("veclib_threads") == 2
        and row.get("omp_threads") == 2
        and row.get("compression_method") == "svd"
        and row.get("dtype") == "complex128"
    ]
    _write_csv(args.results_root / "finalist_seed_runs.csv", finalist_runs)
    exact_times = [
        float(row["total_time_s"])
        for row in finalist_runs
        if row.get("matches_expected_bitstring") is True
        and row.get("total_time_s") is not None
    ]
    if exact_times:
        _write_csv(
            args.results_root / "finalist_seed_summary.csv",
            [
                {
                    "configuration": "finalist_seed_runs",
                    "seed_count": len(exact_times),
                    "median_total_time_s": statistics.median(exact_times),
                    "min_total_time_s": min(exact_times),
                    "max_total_time_s": max(exact_times),
                    "spread_s": max(exact_times) - min(exact_times),
                    "required_seed_count": 5,
                    "five_seed_complete": len(exact_times) >= 5,
                }
            ],
        )
    complex64_finalists = [
        row
        for row in runs
        if row.get("seed") in finalist_seeds
        and row.get("max_bond") == 512
        and row.get("cutoff") == 0.0006
        and row.get("svd_isolation_min_elements") == 131072
        and row.get("veclib_threads") == 2
        and row.get("omp_threads") == 2
        and row.get("compression_method") == "svd"
        and row.get("dtype") == "complex64"
    ]
    _write_csv(args.results_root / "complex64_finalist_seed_runs.csv", complex64_finalists)
    complex64_exact_times = [
        float(row["total_time_s"])
        for row in complex64_finalists
        if row.get("matches_expected_bitstring") is True
        and row.get("total_time_s") is not None
    ]
    if complex64_exact_times:
        _write_csv(
            args.results_root / "complex64_finalist_seed_summary.csv",
            [
                {
                    "configuration": "complex64_finalist_seed_runs",
                    "seed_count": len(complex64_exact_times),
                    "median_total_time_s": statistics.median(complex64_exact_times),
                    "min_total_time_s": min(complex64_exact_times),
                    "max_total_time_s": max(complex64_exact_times),
                    "spread_s": max(complex64_exact_times) - min(complex64_exact_times),
                    "required_seed_count": 5,
                    "five_seed_complete": len(complex64_exact_times) >= 5,
                }
            ],
        )
    _write_csv(
        args.results_root / "threading_comparison.csv",
        [
            row
            for row in runs
            if row.get("veclib_threads") is not None
            and row.get("omp_threads") is not None
        ],
    )
    _plot(args.results_root, dynamics)
    print(f"wrote {len(runs)} run rows and {len(dynamics)} dynamics rows")


if __name__ == "__main__":
    main()
