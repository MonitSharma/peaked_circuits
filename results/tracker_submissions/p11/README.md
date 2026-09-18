# P11 — Helios-1 hardware run

## Run identity

- Circuit: `P11_hqap_1999.qasm`
- Backend: Quantinuum `Helios-1`
- Job: `c902a6a1-0e91-48cf-b5ba-44831fcc7726`
- Requested shots: **50**
- Corrected shots analyzed: **50**
- Reported cost: **282.98 HQC**
- Status: `COMPLETED`

## Hardware result and recovery

The provider framing reconstructed 51 records, but record 46 was an exact
duplicate of record 0. We removed that duplicate from the active analysis and
retained the raw 51-record reconstruction for auditability. No hidden target
was used during recovery.

![P11 frequency and distance histogram](figures/frequency_and_distance.png)

### Weighted Observed Medoid

The weighted observed medoid selects the observed string with the smallest
total Hamming distance to all 50 active shots, weighting repeated strings by
their frequency. It recovered the exact accepted answer:

```text
10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000
```

### Cluster Consensus

Cluster consensus identifies the dominant group of nearby observed strings and
computes the common bit value at each position. It independently recovered the
exact accepted answer:

```text
10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000
```

Both methods agreed, and the resulting bitstring was externally accepted.

## Timing

The provider metadata reports 10,732.063968 s of queue time and 229.924343 s
of hardware execution time. See [`timing.md`](timing.md).

## Contents

- [`quantum/`](quantum/) — source QASM, submitted bitcode, provider results,
  metadata, and checksums.
- [`classical/`](classical/) — corrected shots, recovery analyses, and the raw
  duplicate-frame diagnostic.
- [`protocol/`](protocol/) — run and routing documentation.
