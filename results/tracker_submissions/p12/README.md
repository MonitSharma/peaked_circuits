# P12 — Helios-1 hardware Batch 001

## Run identity

- Circuit: `peaked_circuit_P12_Hqap_98x2457.qasm`
- Backend: Quantinuum `Helios-1`
- Job: `d5cba0df-a7aa-459e-ac51-8092645c059f`
- Job name: `p12_physical_sqd`
- Requested shots: **200**
- Reconstructed shots: **200**
- Reported cost: **1,373.4 HQC**
- Status: `COMPLETED`

## Hardware result and recovery

The provider response contained five fused `END` markers. Structural repair
yielded 205 diagnostic cycles and 200 reconstructed shots after excluding five
exact segment-overlap replicas. No hidden target was used during recovery.

![P12 frequency and distance histogram](figures/frequency_and_distance.png)

### Most Frequent String

The most frequent string is the exact 98-bit string that occurred most often
in the reconstructed shot sample:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

### Weighted Observed Medoid

The weighted observed medoid is the observed string that minimizes the total
Hamming distance to all reconstructed shots, with repeated strings weighted by
their observed frequency. It represents the center of the noisy measured
distribution:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

### Cluster Consensus

Cluster consensus identifies the dominant group of nearby observed strings and
computes the common bit value at each position within that group. This reduces
scattered hardware errors while preserving the common structure:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

All three methods agreed, and the resulting bitstring was externally accepted.

## Timing

The provider record gives 4,580.972377 s from submission to completion and
4,160.855590 s from the outer running timestamp to completion. A nested result
item implies 237.588 s of runtime. These are distinct provider timing fields;
see [`timing.md`](timing.md).

## Contents

- [`quantum/`](quantum/) — source QASM, submitted QIR/bitcode, provider and
  backend metadata, raw result, repaired framing, and checksums.
- [`classical/`](classical/) — reconstructed shots, counts, recovery analyses,
  validation records, and timing source.
- [`protocol/`](protocol/) — runbook and experiment documentation.
- [`timing.md`](timing.md) and [`solution_summary.md`](solution_summary.md) —
  report-ready summaries.
