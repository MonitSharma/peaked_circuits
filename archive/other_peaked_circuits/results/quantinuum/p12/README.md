# P12 — Helios-1 hardware Batch 001

## Run identity

- Circuit: `peaked_circuit_P12_Hqap_98x2457.qasm`
- Backend: Quantinuum `Helios-1`
- Job: `d5cba0df-a7aa-459e-ac51-8092645c059f`
- Job name: `p12_physical_sqd`
- Requested shots: 200
- Reconstructed shots: 200
- Reported cost: 1,373.4 HQC
- Status: `COMPLETED`

## Timing

The provider record gives 4,580.972377 s from submission to completion and
4,160.855590 s from the outer running timestamp to completion. A nested result
item implies 237.588 s of runtime. These are distinct provider timing fields;
see [`timing.md`](timing.md).

Classical reconstruction and analysis were performed locally, but the retained
repository artifacts do not include classical start/end timestamps or an
elapsed-time field. The historical classical wall time is therefore **not
recorded**.

## How the result was obtained

The provider response contained five fused `END` markers. The framing was
repaired structurally, yielding 205 diagnostic cycles and 200 reconstructed
shots after excluding the five exact segment-overlap replicas. The raw result,
repaired framing artifact, reconstruction manifest, canonical shots, counts,
collision analysis, and validation checks are all preserved.

Note: `quantum/raw_result.json` retains its historical filename, but its
contents are ASCII provider-framing text rather than JSON. The parsed/repaired
and reconstructed records are the files under `quantum/` and `classical/raw/`.

The target-blind analysis compared most-frequent, bitwise majority, weighted
observed medoid, and cluster consensus. The most-frequent, weighted-medoid,
and cluster-consensus methods agreed on the final externally verified answer;
the coordinate-wise majority differed at 13 positions and was retained as a
provenance candidate rather than silently replaced.

## Contents

- [`quantum/`](quantum/) — source QASM, submitted QIR/bitcode, provider job and
  backend metadata, raw result, repaired framing, and checksums.
- [`classical/`](classical/) — reconstructed shots, counts, collision and
  validation analyses, retrieval records, and timing source.
- [`protocol/`](protocol/) — candidate freeze, preflight, runbook, checklist,
  Batch 002 plan, and support correspondence.
- [`timing.md`](timing.md) and [`solution_summary.md`](solution_summary.md) —
  report-ready summaries.
