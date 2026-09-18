# P11/P12 positive-control audit

Local, target-independent reanalysis of saved canonical shot records. No provider submission, HQC spend, or hidden-target lookup was performed.

## Results

| Problem | Reconstructed shots | Unique strings | Accepted string recovered by | Max multiplicity | Mean pairwise Hamming |
|---|---:|---:|---|---:|---:|
| P11 | 51 | 50 | weighted_observed_medoid, cluster_consensus | 2 | 41.971765 |
| P12 | 200 | 198 | most_frequent, weighted_observed_medoid, cluster_consensus | 3 | 48.530251 |

## Interpretation

- P11 is a positive control for medoid/cluster recovery: those two methods return the externally accepted 98-bit string, while the simple mode does not.
- P12 is a stronger positive control: most-frequent, weighted observed medoid, and cluster consensus return the externally accepted string; bitwise majority is 13 bits away.
- This is verification of the local analysis and saved-data handling, not a classical simulation of either circuit.
- The audit does not independently re-fetch provider chunks. P11's saved shot file contains 51 records despite a 50-shot request; P12's saved reconstruction contains 200 records after five framing cycles were excluded from a 205-cycle payload.
- P6 must therefore be compared against this corrected positive-control behavior, not against its earlier SDK-assembled apparent repeats.

## Reproducibility

The machine-readable report is `audit.json`; all input paths and SHA-256 hashes are recorded there.
