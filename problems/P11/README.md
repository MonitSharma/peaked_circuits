# P11 — hardware recovery record

## Status

`SOLVED_HARDWARE`: the recovered 98-bit answer was externally accepted. This
is a recovery result, not a standalone quantum-advantage claim.

## Circuit

`P11_hqap_1999`: 98 qubits and 1,999 CZ gates. The source is preserved in the
evidence package byte-for-byte. SHA-256:
`1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`.

## Hardware run

Quantinuum Helios-1 job `c902a6a1-0e91-48cf-b5ba-44831fcc7726` requested 50
shots, returned 51 complete 98-bit records, and cost 282.98 HQC. Provider
metadata reports 229.924343 s execution and 10,732.063968 s queue time. The
submitted bitcode SHA-256 is
`a25a9a74e2aa99c4f76250448b4721511a5d8f01bc4d70db1f45d4a3c41ab465`.

## Target-blind analysis and recovery

The final five provider frames were fused; global 98-label chunking recovered
51 records without truncating the data. Mode, radius-31 cluster, cluster
consensus, Hamming diagnostics, and bootstrap outputs were computed from the
normalized records. The observed mode multiplicity and cluster size were both
2, so the target-blind evidence is weak and exploratory.

## External verification

The later externally reported answer is kept separate in
[`results/tracker_submissions/p11/solution_summary.md`](../../results/tracker_submissions/p11/solution_summary.md).
It was not used as an analysis input. The normalized project status is
`SOLVED_HARDWARE` with external verification reported separately; this is not a
quantum-advantage claim.

## Classical branch history

The earlier classical-method work is preserved in
[`classical_history/`](classical_history/). It is kept separate from the
hardware result so historical nonconvergence is not confused with the later
accepted hardware recovery.

## Evidence and reproduction

Start at the [P11 tracker package](../../results/tracker_submissions/p11/) and
its [package README](../../results/tracker_submissions/p11/TRACKER_SUBMISSION.md).
An auditor can inspect the raw payload, provider metadata, canonical shots,
analysis JSON/Markdown, and checksums without rerunning hardware.
