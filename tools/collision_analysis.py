"""Target-blind collision/cluster analysis for reconstructed Batch 001."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path

from scipy.stats import poisson


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
        pair_stats[str(radius)] = {"observed_pairs": observed, "uniform_expected_pairs": expected, "poisson_upper_tail": poisson.sf(observed - 1, expected)}
    cluster = [shot for shot in shots if hamming(shot, mode) <= 31]
    cluster_candidate = "".join("1" if sum(shot[index] == "1" for shot in cluster) > len(cluster) / 2 else "0" for index in range(98))
    cluster_expected = len(shots) * hamming_volume(98, 31) / (2**98)
    report = {
        "schema_version": "1.0",
        "source_shots": 200,
        "source_counts_sha256": hashlib.sha256(shot_path.read_bytes()).hexdigest(),
        "mode_string": mode,
        "mode_multiplicity": multiplicity,
        "mode_indices": [index for index, shot in enumerate(shots) if shot == mode],
        "pair_statistics": pair_stats,
        "cluster_radius": 31,
        "cluster_shots": len(cluster),
        "cluster_uniform_expected_shots": cluster_expected,
        "cluster_uniform_poisson_upper_tail": poisson.sf(len(cluster) - 1, cluster_expected),
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
        "primary_endpoint": "exact_match_count_of_pre_registered_string",
        "secondary_endpoints": ["pair_counts_at_radii_0_1_20_30", "cluster_mass_radius_31", "cluster_restricted_majority"],
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

| Radius | Observed pairs | Uniform expected pairs | Poisson upper-tail diagnostic |
|---:|---:|---:|---:|
""" + "\n".join(f"| {radius} | {pair_stats[str(radius)]['observed_pairs']} | {pair_stats[str(radius)]['uniform_expected_pairs']:.6g} | {pair_stats[str(radius)]['poisson_upper_tail']:.3e} |" for radius in (0, 1, 20, 30)) + f"""

The uniform-null expected cluster mass at radius 31 is `{cluster_expected:.6g}` shots; the observed cluster contains `{len(cluster)}` shots. These p-values are diagnostics against a deliberately simple uniform null, not a quantum-advantage claim and not a substitute for a circuit-specific classical baseline.

The exact-match string and endpoints are recorded in `hardware_campaign/batch_001/collision_hypothesis.json` for independent Batch 002 confirmation. No hidden target was accessed.
""")
    print(json.dumps({"mode_multiplicity": multiplicity, "cluster_shots": len(cluster), "mode_indices": report["mode_indices"], "cluster_candidate_distance": report["cluster_candidate_hamming_to_mode"]}, indent=2))


if __name__ == "__main__":
    main()
