# Batch 001 collision/cluster analysis

This analysis is target-blind and uses the reconstructed 200 shots. Multiplicity and Hamming-distance statistics are invariant under provider-label permutations; only the identity of the displayed string depends on the verified mapping.

- Mode string: `10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100`
- Mode multiplicity: **3** at indices `[90, 158, 178]`
- Cluster radius: **31**
- Cluster size: **16**
- Cluster-restricted majority: `10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100`
- Cluster candidate distance from mode: **0**
- Mean pairwise Hamming distance: **48.530251**

## Collision statistics

| Radius | Observed pairs | Uniform expected pairs |
|---:|---:|---:|
| 0 | 3 | 6.27933e-26 |
| 1 | 6 | 6.21654e-24 |
| 20 | 25 | 2.85773e-05 |
| 30 | 68 | 1.55378 |

Pair counts are descriptive only. Pair events are dependent, so no Poisson tail is reported for them. The defensible uniform-null bounds are: multiplicity at least 3, `1.308e-53`; multiplicity at least 4, `2.032e-81`. The fixed-centre radius-31 cluster has expected mass `0.0354534` shots and observed mass `16`, with binomial upper tail `1.560e-37`. Centre-based look-elsewhere union bounds are `2.734e-27` for at least 13 neighbours and `1.408e-32` for at least 15 neighbours.

Radius 31 was selected after inspecting the Batch 001 distance distribution. It is now frozen prospectively for Batch 002 and must be applied to the fixed pre-registered Batch 001 mode, not to a newly selected Batch 002 cluster. These are diagnostics against a deliberately simple uniform null, not a quantum-advantage claim and not a substitute for a circuit-specific classical baseline.

The exact-match string and endpoints are recorded in `hardware_campaign/batch_001/collision_hypothesis.json` for independent Batch 002 confirmation. No hidden target was accessed.
