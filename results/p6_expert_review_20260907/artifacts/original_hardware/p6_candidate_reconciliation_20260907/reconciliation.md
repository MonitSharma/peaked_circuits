# P6 candidate reconciliation across prior methods and 300 hardware shots

> SUPERSEDED: Confirmed qnexus chunk-assembly defect duplicated first frames.
> These frequency counts and candidate-support claims are invalid. See
> ../p6_chunk_audit_20260907/README.md and the corrected original-chunk analysis.

Date: 2026-09-07  
Analysis type: target-blind, offline, no provider submission.

## Conclusion

The reconciliation does not produce a new verified candidate.  The 300-shot
hardware sample has no tight cluster that is reproducible across all three
batches.  The previously reported overlap scores were retained as descriptive
post-hoc information only; they were not used to construct or select a new
string.

## Hardware comparison

| Candidate | Nearest hardware shot | Mean Hamming distance | Shots within 15 bits | Batch support |
|---|---:|---:|---:|---|
| Pooled bitwise majority | 12 | 27.73 | 3 | 1, 0, 2 |
| Pooled medoid | 0 | 28.55 | 3 | 2, 0, 1 |
| Batch 001 mode | 0 | 29.85 | 4 | 4, 0, 0 |
| Batch 002 mode | 0 | 29.76 | 5 | 0, 5, 0 |
| Batch 003 mode | 0 | 30.46 | 5 | 0, 0, 5 |

The three hardware modes are batch-specific.  Each appears only in its own
batch and none recurs in all three batches.  The pooled bitwise majority is
closer on average because it is a coordinate-wise aggregate, but it is not an
observed string and has no concentrated support.

## Prior classical candidates

The classical candidates were also compared against every reconstructed shot.
None had a reproducible <=15-bit hardware neighbourhood across all batches.
The best score-constrained classical candidate had the previously reported
40/62 overlap, but that is a post-hoc target score and the candidate has not
been validated by the hardware distribution.

The candidate-family coordinate consensus was:

`11101011111111011010111100111011110100000100000011000011110000`

This is **not recommended as a new submission candidate**.  It is a synthetic
majority of heterogeneous classical and hardware-derived strings, not a
directly observed output or a result supported by an independent recurrence.

The candidate-family medoid was the original MettleQ candidate, but its
nearest hardware support was not reproducible across batches either.

## Leave-one-source-out check

Removing one source changed the candidate-family consensus by 4–12 bits.
That sensitivity means the consensus is dependent on which candidate sources
are included; it is not a stable answer.

## Interpretation of the earlier overlap scores

The 33/62, 34/62, 35/62, 38/62, and 40/62 values are useful for documenting
how previous guesses performed against the hidden target.  They cannot be
used as an ordinary independent training signal for a new guess, because doing
so would leak information from the answer-checking endpoint into the
candidate-generation process.

## Recommendation

If a final exploratory try is required, the only defensible new directly
observed string is the Batch 003 mode:

`01111001011111011100111001100001001110001010000011010011110001`

That remains a low-confidence exploratory guess, not a solution.  No other
new string from this reconciliation has enough independent evidence to merit
promotion.

Machine-readable details are in `reconciliation.json`; the reproducible code
is `tools/reconcile_p6_candidates.py`.
