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

| Radius | Observed pairs | Uniform expected pairs | Poisson upper-tail diagnostic |
|---:|---:|---:|---:|
| 0 | 3 | 6.27933e-26 | 4.127e-77 |
| 1 | 6 | 6.21654e-24 | 8.016e-143 |
| 20 | 25 | 2.85773e-05 | 1.621e-139 |
| 30 | 68 | 1.55378 | 9.016e-85 |

The uniform-null expected cluster mass at radius 31 is `0.0354534` shots; the observed cluster contains `16` shots. These p-values are diagnostics against a deliberately simple uniform null, not a quantum-advantage claim and not a substitute for a circuit-specific classical baseline.

The exact-match string and endpoints are recorded in `hardware_campaign/batch_001/collision_hypothesis.json` for independent Batch 002 confirmation. No hidden target was accessed.
