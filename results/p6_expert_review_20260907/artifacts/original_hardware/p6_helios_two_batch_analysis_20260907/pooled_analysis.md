# P6 two-batch pooled analysis

> SUPERSEDED: Confirmed qnexus chunk-assembly defect duplicated first frames.
> These frequency counts and candidate-support claims are invalid. See
> ../p6_chunk_audit_20260907/README.md and the corrected original-chunk analysis.

Both 100-shot batches were analyzed independently before pooling. The pooled
dataset contains the first 100 reconstructed frames from each batch, following
the predeclared fixed-width 62-record reconstruction rule.

## Independent results

| Dataset | Mode/cluster candidate | Count | Unique strings |
|---|---|---:|---:|
| Batch 001 | `01001001111111011000101110111001110111101110010011000011111101` | 4/100 | 97 |
| Batch 002 | `10100100010110100010001111100110001100001100100111100101111101` | 5/100 | 96 |

The two mode/cluster candidates are 33 bits apart. In each batch, weighted
medoid and coordinate-wise majority selected different candidates.

## Pooled result

The pooled mode/cluster candidate is the Batch 002 candidate at 5/200. The
Batch 001 candidate appears 4/200. The pooled medoid and majority remain
different, so pooling does not produce a stable consensus; it only promotes
the Batch 002 mode by one occurrence.

## Decision

No reproducible P6 candidate was recovered. The two batches are preserved as
negative/ambiguous hardware evidence, not as a confirmation of either string.
The planned confirmation job remains unsubmitted. Any further hardware spend
requires a new pre-registered discovery method or a justified larger-shot
design; it must not target either post-hoc mode.
