# P11 — Helios-1 hardware run

## Run identity

- Circuit: `P11_hqap_1999.qasm`
- Backend: Quantinuum `Helios-1`
- Job: `c902a6a1-0e91-48cf-b5ba-44831fcc7726`
- Job name: `p11-physical-50-20260828`
- Requested shots: 50
- Raw reconstructed records: 51
- Corrected independent records analyzed: 50
- Reported cost: 282.98 HQC
- Status: `COMPLETED`

## Timing

The provider metadata reports 10,732.063968 s of queue time and
229.924343 s of execution time. The retained run document rounds these to
approximately 10,732 s and 230 s. See [`timing.md`](timing.md) for the
reporting-safe wording and timestamps available in the artifacts.

The original run did not retain classical start/end timestamps. We therefore
reran the deterministic packaged reanalysis and measured it locally: **0.005715375
seconds wall time** for loading, validating, counting, and computing the four
recovery methods. See [`classical/runtime_audit.json`](classical/runtime_audit.json).

## How the result was handled

The provider fused shot frames near the end of the result. The raw payload was
reconstructed into 51 complete 98-bit records, but reconstructed record 46 is
an exact duplicate of record 0. It is therefore retained as a raw diagnostic
and removed from the active 50-shot analysis. See
[`classical/raw/duplicate_frame_repair.json`](classical/raw/duplicate_frame_repair.json)
and [`classical/raw_reconstructed_51/`](classical/raw_reconstructed_51/).

The corrected analysis uses the observed mode, weighted observed medoid, and
cluster-consensus diagnostics. Pair counts are descriptive only; no invalid
independent-Poisson p-values are used.

The target-blind retained analysis found only a weak exploratory structure
(mode multiplicity 2; radius-31 cluster size 2). A later externally reported
answer is recorded in [`solution_summary.md`](solution_summary.md) and should
not be confused with the target-blind analysis candidate.

## Contents

- [`quantum/`](quantum/) — source QASM, submitted bitcode, provider job/result
  metadata, raw provider outputs, and checksums.
- [`classical/`](classical/) — corrected 50-shot normalization, recovery,
  canonical shots, and analysis outputs; the raw 51-record diagnostic is under
  `classical/raw_reconstructed_51/`.
- [`protocol/`](protocol/) — run and routing documentation.
- [`timing.md`](timing.md) and [`solution_summary.md`](solution_summary.md) —
  report-ready summaries.
