from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import matplotlib

# This package writes figures to disk; it never needs an interactive GUI.  On
# macOS, Matplotlib's auto-selected ``macosx`` backend can abort the entire
# Python process when the CLI or tests run without a window server.  Select a
# deterministic headless backend before importing pyplot.
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .bootstrap import bootstrap_recovery
from .hashing import hash_config
from .models import RecoveryCandidate, RecoveryReport, SyntheticExperimentConfig, utc_now
from .recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    score_as_dict,
    weighted_observed_medoid,
)
from .reporting import git_state, package_versions, repository_root, write_json
from .synthetic import (
    aggregate_shots,
    asymmetric_readout_shots,
    independent_bit_flip_shots,
    mixture_shots,
    random_target,
)

Method = Callable[[Mapping[str, int]], RecoveryCandidate]
METHODS: list[Method] = [
    most_frequent_string,
    bitwise_majority_string,
    weighted_observed_medoid,
    cluster_consensus,
]


def _settings(config: SyntheticExperimentConfig, smoke: bool) -> list[dict[str, Any]]:
    shots = config.shot_counts[:2] if smoke else config.shot_counts
    rates = (
        config.models["independent"]["error_rates"][:2]
        if smoke
        else config.models["independent"]["error_rates"]
    )
    values = [{"model": "independent", "shots": n, "error_rate": p} for p in rates for n in shots]
    if not smoke:
        values.extend({"model": "asymmetric", "shots": n} for n in shots)
        values.extend({"model": "mixture", "shots": n} for n in shots)
    return values


def _generate(
    target: str, setting: dict[str, Any], config: SyntheticExperimentConfig, seed: int
) -> list[str]:
    shots = setting["shots"]
    if setting["model"] == "independent":
        return independent_bit_flip_shots(
            target, shots, error_probability=setting["error_rate"], seed=seed
        )
    if setting["model"] == "asymmetric":
        model = config.models["asymmetric"]
        return asymmetric_readout_shots(
            target, shots, p_1_to_0=model["p_1_to_0"], p_0_to_1=model["p_0_to_1"], seed=seed
        )
    model = config.models["mixture"]
    return mixture_shots(
        target,
        shots,
        target_weight=model["target_weight"],
        secondary_weight=model["secondary_weight"],
        uniform_weight=model["uniform_weight"],
        seed=seed,
    )


def run_synthetic_benchmark(
    config: SyntheticExperimentConfig, output_dir: Path, figures_dir: Path, *, smoke: bool = False
) -> dict[str, Any]:
    root = repository_root(output_dir)
    commit, dirty = git_state(root) if root else (None, None)
    target = config.targets.get("explicit_target") or random_target(
        config.number_of_qubits, seed=config.seed
    )
    if len(target) != config.number_of_qubits:
        raise ValueError("Synthetic target width does not match configuration")
    rows: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    replicates = min(config.bootstrap_replicates, 3) if smoke else config.bootstrap_replicates
    for index, setting in enumerate(_settings(config, smoke)):
        seed = config.seed + index
        counts = aggregate_shots(_generate(target, setting, config, seed))
        candidates = [method(counts) for method in METHODS]
        scores = {
            candidate.method_name: score_as_dict(candidate.canonical_bitstring, target)
            for candidate in candidates
        }
        bootstraps: list[dict[str, Any]] = []
        for method_index, method in enumerate(METHODS):
            bootstrap_model = bootstrap_recovery(
                counts, method, replicates=replicates, seed=seed + 1000 + method_index
            ).model_copy(update={"git_commit": commit, "git_dirty": dirty})
            bootstraps.append(bootstrap_model.model_dump(mode="json"))
        for candidate, bootstrap_data in zip(candidates, bootstraps, strict=True):
            score = scores[candidate.method_name]
            rows.append(
                {
                    **setting,
                    "seed": seed,
                    "method": candidate.method_name,
                    "unique_strings": len(counts),
                    "exact_recovery": score["exact_match"],
                    "correct_bits": score["correct_bits"],
                    "percentage_correct": score["percentage_correct"],
                    "hamming_distance": score["hamming_distance"],
                    "runtime_seconds": candidate.runtime_seconds,
                    "bootstrap_exact_stability": bootstrap_data["exact_match_stability"],
                    "bootstrap_stable_bits": bootstrap_data["stable_bits"],
                }
            )
        reports.append(
            {
                "setting": setting,
                "seed": seed,
                "recovery": RecoveryReport(
                    candidates=candidates,
                    method_agreement=method_agreement(candidates),
                    scores=scores,
                    random_seed=seed,
                    package_versions=package_versions(),
                    git_commit=commit,
                    git_dirty=dirty,
                ).model_dump(mode="json"),
                "bootstrap": bootstraps,
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(output_dir / "synthetic_summary.csv", index=False)
    payload = {
        "schema_version": "1.0",
        "created_at": utc_now().isoformat(),
        "git_commit": commit,
        "git_dirty": dirty,
        "seed": config.seed,
        "configuration": config.model_dump(mode="json"),
        "smoke": smoke,
        "target_disclosure": "synthetic_only",
        "synthetic_target": target,
        "settings": reports,
        "summary_rows": rows,
        "package_versions": package_versions(),
        "input_hashes": {"synthetic_configuration": hash_config(config.model_dump(mode="json"))},
    }
    write_json(output_dir / "synthetic_report.json", payload)
    best = dataframe.groupby("method")["percentage_correct"].mean().sort_values(ascending=False)
    markdown = "# Synthetic benchmark\n\nThis report uses a planted synthetic target; it says nothing about the hidden P12 target.\n\n"
    markdown += f"Seed: `{config.seed}`; settings: {len(reports)}; bootstrap replicates per method/setting: {replicates}.\n\n"
    markdown += (
        "## Mean correct-bit percentage\n\n"
        + "\n".join(f"- {name}: {value:.3f}%" for name, value in best.items())
        + "\n"
    )
    (output_dir / "synthetic_report.md").write_text(markdown)
    _plots(dataframe, reports, figures_dir, config.seed)
    return payload


def _plots(
    frame: pd.DataFrame, reports: list[dict[str, Any]], figures_dir: Path, seed: int
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    source = "results/synthetic/synthetic_report.json"

    def save(name: str) -> None:
        plt.figtext(0.01, 0.01, f"Seed {seed}; source: {source}", fontsize=7)
        plt.tight_layout()
        plt.savefig(figures_dir / name, dpi=300, metadata={"Seed": str(seed), "Source": source})
        plt.close()

    independent = frame[frame["model"] == "independent"]
    plt.figure(figsize=(8, 5))
    for method, group in independent.groupby("method"):
        values = group.groupby("shots")["percentage_correct"].mean()
        plt.plot(values.index, values.values, marker="o", label=method)
    plt.title("Synthetic recovery accuracy versus shots")
    plt.xlabel("Shots (count)")
    plt.ylabel("Correct bits (%)")
    plt.ylim(0, 100)
    plt.legend(fontsize=7)
    save("recovery_accuracy_versus_shots.png")
    plt.figure(figsize=(8, 5))
    for method, group in independent.groupby("method"):
        values = group.groupby("shots")["bootstrap_exact_stability"].mean()
        plt.plot(values.index, values.values, marker="o", label=method)
    plt.title("Candidate bootstrap stability versus shots")
    plt.xlabel("Shots (count)")
    plt.ylabel("Exact stability (fraction)")
    plt.ylim(0, 1)
    plt.legend(fontsize=7)
    save("candidate_stability_versus_shots.png")
    plt.figure(figsize=(8, 5))
    for method, group in independent.groupby("method"):
        values = group.groupby("error_rate")["percentage_correct"].mean()
        plt.plot(values.index, values.values, marker="o", label=method)
    plt.title("Correct-bit percentage versus independent error rate")
    plt.xlabel("Bit-flip probability")
    plt.ylabel("Correct bits (%)")
    plt.ylim(0, 100)
    plt.legend(fontsize=7)
    save("correct_bit_percentage_versus_error_rate.png")
    plt.figure(figsize=(8, 5))
    for method, group in frame.groupby("method"):
        plt.scatter(group["unique_strings"], group["runtime_seconds"], label=method, alpha=0.7)
    plt.title("Recovery runtime versus unique observations")
    plt.xlabel("Unique observed strings (count)")
    plt.ylabel("Runtime (seconds)")
    plt.legend(fontsize=7)
    save("method_runtime_versus_unique_strings.png")
    first = reports[0]
    majority = next(
        c for c in first["recovery"]["candidates"] if c["method_name"] == "bitwise_majority"
    )
    confidence = np.asarray(majority["confidence"]["absolute_margin"])[None, :]
    plt.figure(figsize=(12, 2.5))
    plt.imshow(confidence, aspect="auto", vmin=0, vmax=1, cmap="viridis")
    plt.colorbar(label="Absolute majority margin")
    plt.yticks([])
    plt.xlabel("Canonical logical-qubit index")
    plt.title("Per-bit confidence heat map")
    save("per_bit_confidence_heatmap.png")
    agreement = np.asarray(first["recovery"]["method_agreement"]["pairwise_hamming_distance"])
    methods = first["recovery"]["method_agreement"]["methods"]
    plt.figure(figsize=(6, 5))
    plt.imshow(agreement, cmap="magma")
    plt.colorbar(label="Hamming distance (bits)")
    plt.xticks(range(len(methods)), methods, rotation=35, ha="right")
    plt.yticks(range(len(methods)), methods)
    plt.title("Recovery-method agreement")
    save("method_agreement_hamming_distance_matrix.png")
