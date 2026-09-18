# P6 two-batch offline forensic analysis

> SUPERSEDED: Confirmed qnexus chunk-assembly defect duplicated first frames.
> These frequency counts and candidate-support claims are invalid. See
> ../p6_chunk_audit_20260907/README.md and the corrected original-chunk analysis.

Date: 2026-09-07  
Scope: the already completed Helios-1 Batch 001 and Batch 002 jobs only.  
Provider submissions performed by this analysis: none.

## Executive conclusion

The 200 shots are useful for diagnosing the run, but they do not support a
defensible complete 62-bit P6 answer.  The correct next action is to preserve
the data and stop treating any one decoder output as a solved candidate.

The main evidence is:

- The pooled sample has **193 unique strings out of 200 shots**.
- The pooled mode occurs only **5 times**; the Batch 001 mode occurs 4 times
  and the Batch 002 mode occurs 5 times.
- The two batch modes are **33 Hamming bits apart**.
- The weighted medoid and bitwise majority do not agree with the pooled mode.
- Every one of the 62 bit positions is unresolved under the predeclared
  stability rule `p(1) <= 0.25` or `p(1) >= 0.75`.
- The closest cross-batch pair is 16 bits apart; there are no cross-batch
  pairs at distance 15 or less.

These are descriptive diagnostics, not independent-null p-values.  In
particular, the nearest-neighbour counts must not be exponentiated as if the
pairs were independent.

## What was done

1. Reconstructed fixed-width 62-bit frames from each raw QIR result, using the
   first 100 complete frames from each provider-reported 100-shot batch.
2. Re-ran four decoders independently on Batch 001, Batch 002, and the pooled
   200-shot sample: most frequent string, bitwise majority, weighted observed
   medoid, and cluster consensus.
3. Ran split-half checks within each batch and compared the two batches.
4. Calculated per-position frequencies and a stable-bit ensemble.
5. Calculated descriptive cross-batch nearest-neighbour distances.
6. Ran 250 deterministic bootstrap resamples with replacement.
7. Compared the resulting outputs with the previously available classical and
   hardware candidate pool without using any hidden target or external score
   to select a new candidate.

## Decoder outputs

| Decoder | Pooled 200-shot output | Interpretation |
|---|---|---|
| Most frequent | `10100100010110100010001111100110001100001100100111100101111101` | 5/200; not a reproducible peak |
| Bitwise majority | `11101100110110100000000011010001111101001110010101101101110101` | An ensemble summary, not observed as a string |
| Weighted medoid | `11100100100111101011101110011101111111111110010101101111000001` | Central under Hamming loss, but not a dominant mode |
| Cluster consensus | Same as pooled mode | The selected cluster contains only 5/200 shots |

Batch 001's mode/cluster candidate was
`01001001111111011000101110111001110111101110010011000011111101` (4/100).
Batch 002's mode/cluster candidate was
`10100100010110100010001111100110001100001100100111100101111101` (5/100).
Their Hamming distance is 33/62.

## Stability results

The pooled per-bit frequencies range broadly around 0.5.  No position reaches
the 0.25/0.75 stability threshold, so there is no stable subset from which to
assemble a defensible partial answer.

The bootstrap is also method-dependent:

| Method | Distinct outputs over 250 resamples | Most common output frequency |
|---|---:|---:|
| Most frequent | 55 | 109/250 (43.6%) |
| Bitwise majority | 250 | 1/250 (0.4%) |
| Weighted medoid | 22 | 71/250 (28.4%) |

The most common bootstrap mode is the Batch 002 mode, but its 43.6% recurrence
is driven by resampling the five observed copies and is not independent
confirmation.  The bitwise-majority instability is especially important: a
small change in the resampled shot composition changes many majority bits.

## Cross-batch structure

The nearest-neighbour calculation found:

- minimum cross-batch distance: 16/62;
- median per-shot nearest cross-batch distance: 21/62;
- cross-batch shot pairs at distance <= 15: 0;
- cross-batch shot pairs at distance <= 20: 95, reported only descriptively.

This does not show a shared tight basin.  The 200 shots look like a broad,
high-entropy output distribution with small repeated strings rather than two
independent observations of the same recoverable peak.

## Candidate-pool comparison

The analysis retained the previous MettleQ, D128, score-constrained, D128
extract, D512, batch-mode, pooled-majority, and pooled-medoid candidates.  No
new candidate was promoted from their external overlap scores.  The previously
reported overlaps are post-hoc information and do not repair the lack of
reproducibility in the hardware sample.

## Decision

**Status: `NO_REPRODUCIBLE_FULL_CANDIDATE`.**

The existing 200-shot result should be kept as a negative/diagnostic hardware
result, not discarded.  It can support analysis of framing, routing, noise,
and decoder failure modes.  It should not be presented as an end-to-end P6
solution, and no additional candidate should be claimed solely because it is
the pooled mode, medoid, or majority output.

Machine-readable output and the exact analysis script are saved at:

- `results/hardware/p6_200shot_forensics_20260907/forensics.json`
- `tools/p6_200shot_forensics.py`
