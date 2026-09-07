# P6 four-batch hardware analysis

> SUPERSEDED: Confirmed qnexus chunk-assembly defect duplicated first frames.
> These frequency counts and candidate-support claims are invalid. See
> ../p6_chunk_audit_20260907/README.md and the corrected original-chunk analysis.

Date: 2026-09-07  
Scope: four completed, independently submitted 100-shot Helios-1 batches.

## Result

Batch 004 was retrieved successfully and analyzed with the same fixed-width
62-record reconstruction rule.  It does not produce a recurring candidate.

Across all 400 primary frames there are **386 unique strings**.  The largest
pooled frequency is only **5/400**, tied between the Batch 002 and Batch 003
modes.  The deterministic decoder reports the lexicographically smaller of
the tied strings; this tie-break is not scientific evidence.

No bit position reaches the predeclared stability threshold
`p(1) <= 0.25` or `p(1) >= 0.75`.

## Independent modes

| Batch | Mode / cluster candidate | Count |
|---|---|---:|
| 001 | `01001001111111011000101110111001110111101110010011000011111101` | 4/100 |
| 002 | `10100100010110100010001111100110001100001100100111100101111101` | 5/100 |
| 003 | `01111001011111011100111001100001001110001010000011010011110001` | 5/100 |
| 004 | `01000100100011010111000001111000100011110000111110100111001011` | 4/100 |

Pairwise mode distances are 20–38 bits.  No mode recurs across batches.

## Pooled decoders

| Decoder | Output |
|---|---|
| Most frequent / cluster consensus | `01111001011111011100111001100001001110001010000011010011110001` |
| Bitwise majority | `11101100110111100001000011010101111101001110010101110111100101` |
| Weighted medoid | `11101100110110100000001011000100111100011010000101101110100001` |

The pooled mode/cluster string is only tied at 5 occurrences and was already
tested externally at 33/62.  The pooled bitwise majority is synthetic and was
not observed as a shot.  None should be promoted to a solution.

## Decision

**Status: `NO_REPRODUCIBLE_FULL_CANDIDATE`.**

The fourth batch adds evidence that the output distribution is broad and that
the repeated strings are batch-specific collisions rather than a stable P6
peak.  Further blind hardware shots are unlikely to resolve the answer under
this decoder.  Any next hardware run should require a materially different,
pre-registered method or circuit/readout change.

Raw result and machine-readable analysis are preserved alongside the Batch 004
job record.
