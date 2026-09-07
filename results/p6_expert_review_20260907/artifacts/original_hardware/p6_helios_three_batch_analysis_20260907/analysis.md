# P6 three-batch hardware analysis

> SUPERSEDED: Confirmed qnexus chunk-assembly defect duplicated first frames.
> These frequency counts and candidate-support claims are invalid. See
> ../p6_chunk_audit_20260907/README.md and the corrected original-chunk analysis.

Date: 2026-09-07  
Scope: three completed, independently submitted 100-shot Helios-1 batches.  
New hardware submission during analysis: none.

## Conclusion

The third batch does not establish a reproducible P6 answer.  Across all 300
shots there are **289 unique strings**.  The strongest pooled count is only
5/300, and it is tied between the Batch 002 and Batch 003 modes; the decoder's
deterministic lexicographic tie-break reports the Batch 003 mode as the pooled
mode.  No bit position reaches the predeclared stability threshold.

The result should therefore remain classified as **negative/ambiguous hardware
evidence**, not a solved P6 instance.

## Independent batch results

| Batch | Unique strings | Mode / cluster candidate | Count |
|---|---:|---|---:|
| 001 | 97 | `01001001111111011000101110111001110111101110010011000011111101` | 4/100 |
| 002 | 96 | `10100100010110100010001111100110001100001100100111100101111101` | 5/100 |
| 003 | 96 | `01111001011111011100111001100001001110001010000011010011110001` | 5/100 |

Pairwise Hamming distances between the three batch modes are 33, 20, and 31
bits.  Thus no mode recurs across batches.

## Pooled 300-shot result

The top pooled counts are tied:

- Batch 002 mode: 5/300
- Batch 003 mode: 5/300
- Batch 001 mode: 4/300

The pooled decoder outputs are:

| Decoder | Output |
|---|---|
| Most frequent (lexicographic tie-break) | `01111001011111011100111001100001001110001010000011010011110001` |
| Bitwise majority | `11101100110110000001001011010101111101001110010101111111110101` |
| Weighted medoid | `11101100110110100000001011000100111100011010000101101110100001` |
| Cluster consensus | `01111001011111011100111001100001001110001010000011010011110001` |

The pooled mode is not uniquely supported; it wins only through the
deterministic tie-break.  It must not be promoted to a candidate answer.

## Bit stability

Using the predeclared rule `p(1) <= 0.25` or `p(1) >= 0.75`, **0 of 62 bits**
are stable over the pooled 300 shots.  The bitwise ensemble is therefore only
a descriptive summary, not a recoverable answer.

## Framing and preservation

The three raw provider payloads were preserved and reconstructed using the same
fixed-width 62-record rule used for the earlier analyses.  Each batch supplied
at least 100 complete reconstructed frames; exactly the first 100 frames per
batch were used for the primary comparison.  The raw hashes and framing counts
are recorded in `analysis.json`.

## Decision

The additional 100 shots were useful as an independent reproducibility test,
but pooling did not reveal a stable P6 peak.  Further hardware spending should
not target any of these post-hoc modes.  Any future run would require a new,
pre-registered decoder or a justified change in circuit/readout methodology.

Machine-readable analysis: `analysis.json`.  Retrieval record:
`hardware_campaign/p6_batch_003/job_record.json`.
