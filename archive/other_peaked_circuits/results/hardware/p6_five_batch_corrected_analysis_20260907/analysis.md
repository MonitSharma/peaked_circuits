# P6 corrected five-batch analysis

Batch 005 was retrieved from the original Nexus chunks and analyzed without the
SDK's faulty chunk concatenation. The five batches contain **500 corrected
shots**.

All 500 corrected strings are unique. There is no frequency winner. Any
`most_frequent` output shown in the JSON is only the library's deterministic
lexicographic tie-break among 500 one-count strings; it is not a peak or a
candidate supported by recurrence.

Batch 005 itself also contains 100 unique strings. The earlier repeated-string
peaks came from the SDK's duplicated first-frame assembly and do not survive
chunk-level retrieval.

The five batch decoder summaries disagree, and zero bit positions meet the
predeclared 25%/75% stability threshold. The corrected result remains
`NO_REPRODUCIBLE_FULL_CANDIDATE`.

Batch 005 job ID: `35bab525-cea9-48ac-bdd0-9a3e067a2dea`  
Batch 005 result ID: `9a7f565b-75f5-4541-b03c-3c2929f1ba01`  
Reported cost: 856.04 HQC

Machine-readable analysis: `analysis.json`. Corrected Batch 005 shots are
preserved in `results/hardware/p6_helios_100shot_20260907_batch5/shots.json`.
