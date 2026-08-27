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

Pair counts are descriptive only. Pair events are dependent, so no Poisson tail is reported for them. For discovered Batch 001 structure, the relevant centre-selection-corrected bound is the centre-based union bound: `2.734e-27` for at least 13 neighbours and `1.408e-32` for at least 15 neighbours. The fixed-centre binomial tail `1.560e-37` is prospective Batch 002 operating-characteristic information only; it must not be interpreted as the Batch 001 p-value.

Radius 31 was selected after inspecting the Batch 001 distance distribution. It is now frozen prospectively for Batch 002 and must be applied to the fixed pre-registered Batch 001 mode, not to a newly selected Batch 002 cluster. These are diagnostics against a deliberately simple uniform null, not a quantum-advantage claim and not a substitute for a circuit-specific classical baseline.

## Prospective threshold operating characteristics

For Batch 002, the fixed-centre radius-31 endpoint is the number of shots within radius 31 of the pre-registered Batch 001 mode. Under the simple uniform null with 200 shots, approximate upper-tail probabilities are: mass ≥1 `3.48e-02`, ≥2 `6.11e-04`, ≥3 `7.13e-06`, ≥4 `6.21e-08`, and ≥5 `4.31e-10`. The threshold of 5 is deliberately conservative; masses 1–4 remain weak/directional rather than being promoted to success based on nominal significance.

The exact-match string and endpoints are recorded in `hardware_campaign/batch_001/collision_hypothesis.json` for independent Batch 002 confirmation. No hidden target was accessed.
