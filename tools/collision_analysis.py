"""Target-blind collision/cluster analysis for reconstructed Batch 001."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path

from scipy.stats import binom


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b, strict=True))


def hamming_volume(width: int, radius: int) -> int:
    return sum(math.comb(width, distance) for distance in range(radius + 1))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    shot_path = root / "hardware_campaign/batch_001/reconstruction/reconstructed_200_shots.jsonl"
    shots = [json.loads(line)["canonical_bitstring"] for line in shot_path.read_text().splitlines()]
    counts = Counter(shots)
    mode, multiplicity = min(counts.items(), key=lambda item: (-item[1], item[0]))
    distances = [hamming(a, b) for a, b in itertools.combinations(shots, 2)]
    pair_stats = {}
    for radius in (0, 1, 20, 30):
        observed = sum(distance <= radius for distance in distances)
        expected = math.comb(len(shots), 2) * hamming_volume(98, radius) / (2**98)
        pair_stats[str(radius)] = {"observed_pairs": observed, "uniform_expected_pairs": expected}
    cluster = [shot for shot in shots if hamming(shot, mode) <= 31]
    cluster_candidate = "".join("1" if sum(shot[index] == "1" for shot in cluster) > len(cluster) / 2 else "0" for index in range(98))
    cluster_expected = len(shots) * hamming_volume(98, 31) / (2**98)
    neighbor_probability = hamming_volume(98, 31) / (2**98)
    centre_masses = [sum(hamming(center, shot) <= 31 for shot in shots) for center in shots]
    centre_look_elsewhere_bounds = {
        str(threshold): min(1.0, len(shots) * float(binom.sf(threshold - 1, len(shots) - 1, neighbor_probability)))
        for threshold in (13, 15)
    }
    report = {
        "schema_version": "1.0",
        "source_shots": 200,
        "source_counts_sha256": hashlib.sha256(shot_path.read_bytes()).hexdigest(),
        "mode_string": mode,
        "mode_multiplicity": multiplicity,
        "mode_indices": [index for index, shot in enumerate(shots) if shot == mode],
        "pair_statistics": pair_stats,
        "pair_p_values": None,
        "multiplicity_union_bounds": {
            "at_least_3": math.comb(len(shots), 3) / (2**(98 * 2)),
            "at_least_4": math.comb(len(shots), 4) / (2**(98 * 3)),
        },
        "cluster_radius": 31,
        "cluster_shots": len(cluster),
        "cluster_uniform_expected_shots": cluster_expected,
        "cluster_fixed_centre_binomial_upper_tail": float(binom.sf(len(cluster) - 1, len(shots), neighbor_probability)),
        "cluster_centre_look_elsewhere_bounds": centre_look_elsewhere_bounds,
        "maximum_observed_centre_mass": max(centre_masses),
        "cluster_candidate": cluster_candidate,
        "cluster_candidate_hamming_to_mode": hamming(cluster_candidate, mode),
        "mean_pairwise_hamming_distance": sum(distances) / len(distances),
        "mapping_invariant_statistics": ["mode_multiplicity", "pair_hamming_distances", "cluster_mass"],
        "external_target_scored": False,
    }
    analysis = root / "hardware_campaign/batch_001/analysis/collision_analysis.json"
    analysis.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    hypothesis = root / "hardware_campaign/batch_001/collision_hypothesis.json"
    hypothesis.write_text(json.dumps({
        "schema_version": "1.0", "status": "pre_registered_for_batch_002",
        "source_analysis_sha256": hashlib.sha256(analysis.read_bytes()).hexdigest(),
        "exact_match_string": mode, "exact_match_string_sha256": hashlib.sha256(mode.encode()).hexdigest(),
        "cluster_radius": 31, "cluster_candidate": cluster_candidate,
        "primary_endpoints": ["exact_match_count_of_pre_registered_string", "fixed_centre_cluster_mass_radius_31"],
        "decision_thresholds": {"exact_match_strong_recurrence": 1, "cluster_mass_strong_recurrence": 5, "cluster_mass_weak_directional": [1, 4]},
        "secondary_endpoints": ["descriptive_pair_counts_at_radii_0_1_20_30", "cluster_restricted_majority"],
        "external_target_scored": False, "target_accessed": False,
    }, indent=2, sort_keys=True) + "\n")
    md = root / "results/prephysical/batch_001_collision_analysis.md"
    md.write_text(f"""# Batch 001 collision/cluster analysis

This analysis is target-blind and uses the reconstructed 200 shots. Multiplicity and Hamming-distance statistics are invariant under provider-label permutations; only the identity of the displayed string depends on the verified mapping.

- Mode string: `{mode}`
- Mode multiplicity: **{multiplicity}** at indices `{[index for index, shot in enumerate(shots) if shot == mode]}`
- Cluster radius: **31**
- Cluster size: **{len(cluster)}**
- Cluster-restricted majority: `{cluster_candidate}`
- Cluster candidate distance from mode: **{hamming(cluster_candidate, mode)}**
- Mean pairwise Hamming distance: **{sum(distances) / len(distances):.6f}**

## Collision statistics

| Radius | Observed pairs | Uniform expected pairs |
|---:|---:|---:|
""" + "\n".join(f"| {radius} | {pair_stats[str(radius)]['observed_pairs']} | {pair_stats[str(radius)]['uniform_expected_pairs']:.6g} |" for radius in (0, 1, 20, 30)) + f"""

Pair counts are descriptive only. Pair events are dependent, so no Poisson tail is reported for them. For discovered Batch 001 structure, the relevant centre-selection-corrected bound is the centre-based union bound: `{centre_look_elsewhere_bounds['13']:.3e}` for at least 13 neighbours and `{centre_look_elsewhere_bounds['15']:.3e}` for at least 15 neighbours. The fixed-centre binomial tail `{float(binom.sf(len(cluster) - 1, len(shots), neighbor_probability)):.3e}` is prospective Batch 002 operating-characteristic information only; it must not be interpreted as the Batch 001 p-value.

Radius 31 was selected after inspecting the Batch 001 distance distribution. It is now frozen prospectively for Batch 002 and must be applied to the fixed pre-registered Batch 001 mode, not to a newly selected Batch 002 cluster. These are diagnostics against a deliberately simple uniform null, not a quantum-advantage claim and not a substitute for a circuit-specific classical baseline.

## Prospective threshold operating characteristics

For Batch 002, the fixed-centre radius-31 endpoint is the number of shots within radius 31 of the pre-registered Batch 001 mode. Under the simple uniform null with 200 shots, approximate upper-tail probabilities are: mass ≥1 `3.48e-02`, ≥2 `6.11e-04`, ≥3 `7.13e-06`, ≥4 `6.21e-08`, and ≥5 `4.31e-10`. The threshold of 5 is deliberately conservative; masses 1–4 remain weak/directional rather than being promoted to success based on nominal significance.

The exact-match string and endpoints are recorded in `hardware_campaign/batch_001/collision_hypothesis.json` for independent Batch 002 confirmation. No hidden target was accessed.
""")
    print(json.dumps({"mode_multiplicity": multiplicity, "cluster_shots": len(cluster), "mode_indices": report["mode_indices"], "cluster_candidate_distance": report["cluster_candidate_hamming_to_mode"]}, indent=2))


if __name__ == "__main__":
    main()
