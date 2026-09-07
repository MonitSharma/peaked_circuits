# P6 result correction: confirmed SDK chunk-assembly defect

Update: Batch 005 was later retrieved directly and analyzed in
`results/hardware/p6_five_batch_corrected_analysis_20260907/`. The corrected
five-batch total is 500 shots and all 500 are unique.

This audit supersedes the earlier 100/200/300/400-frame frequency analyses and plots.
Original files remain preserved as evidence, but their repeated strings are not hardware recurrences.

## Evidence

The installed qnexus `fetch_qsys_result_by_id` joins each subsequent chunk using
`result.results += prev_str + next_str + "END\t0\n"`, where `prev_str` is the
entire first frame and metadata before the first END. This replays the first shot
once per additional chunk. The exact installed source is archived in
`sdk_assembly_source.txt`.

We fetched the original chunk responses directly through the authenticated API
endpoint used by the SDK. Replaying the faulty join reproduces each saved payload
exactly. This establishes a client-side assembly defect without requiring an
assumption about duplicate hardware shots. No deduplication or truncation is used
in the corrected data: each original chunk is parsed separately and all its
complete frames are retained.

| Batch | Original chunk shot counts | True shots | Unique strings |
|---|---|---:|---:|
| 001 | 25, 30, 25, 20 | 100 | 100 |
| 002 | 30, 14, 17, 25, 14 | 100 | 100 |
| 003 | 4, 30, 25, 30, 11 | 100 | 100 |
| 004 | 25, 30, 15, 30 | 100 | 100 |

Pooled: **400 shots, 400 unique strings, every count equals one.**
The former four modes are ordinary first shots, each occurring once. Their
external overlap scores do not validate the frequency interpretation.

## Circuit audit

The frozen source QASM is byte-identical to the original downloaded P6 QASM.
Rebasing that source and adding explicit logical-qubit-to-result measurements
reproduces the saved QIR text exactly. Reassembling that IR reproduces the
submitted bitcode byte for byte. The QIR artifacts freshly downloaded for all
four jobs match the same local bitcode. Canonical LLVM IR also matches; the
initial raw textual comparison differed only before IR normalization.
This is reproducibility evidence for the local conversion pipeline, not a
full 62-qubit statevector equivalence proof or an audit of internal device compilation.

## Corrected analysis

`audit.json` includes the four independent decoder runs followed by pooled
analysis. `shots_400.json` contains all corrected shots and each batch directory
contains original chunk responses, its shot array, and the provider input bitcode.
Mode selection among 400 equal counts is arbitrary. A cluster or majority output
does not become a validated answer because the data have been repaired.

The earlier 75% bit-frequency threshold is a descriptive heuristic, not a
criterion for whether a peaked circuit has a recoverable solution. Lack of strong
marginal biases does not prove absence of a peak. Likewise, these samples alone
do not prove more shots can never help or establish a hardware noise cause.

## Next steps

Pause additional P6 submissions while assessing signal and noise from corrected
data. Stop recommending tied modes. Confirm the SDK defect and fixed version with
Quantinuum using the accompanying draft; no message has been sent. Use per-chunk
retrieval for future results until a fixed SDK is verified. Audit P11/P12 and other
QIR results for the same defect before relying on their recurrence statistics;
this does not invalidate independently verified answer strings.

Reproduce: `PYTHONPATH=src .venv/bin/python tools/audit_p6_chunks.py` (read-only
provider calls; creates local audit artifacts; submits no jobs).
