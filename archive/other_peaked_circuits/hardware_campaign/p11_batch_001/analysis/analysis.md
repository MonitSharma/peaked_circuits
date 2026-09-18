# P11 50-shot Helios analysis

Independent, target-blind exploratory analysis of the returned P11 hardware data. This is not hidden-target verification and is not a quantum-advantage claim.

## Result accounting

- Requested shots: **50**
- Complete returned shots: **51**
- Explanation: the provider fused the final five shot frames in one section; the raw payload contains 4,998 labeled measurements, exactly 51 × 98.
- Reported cost: **282.98 HQC**

## Recovery diagnostics

- Mode: `01111110011011000111010110011001001001111011110000001001101101011011101111000010110011000001011001`
- Mode multiplicity: **2**
- Mode indices (zero-based): `[0, 46]`
- Radius-31 cluster around observed mode: **2** shots
- Cluster-restricted majority: `01111110011011000111010110011001001001111011110000001001101101011011101111000010110011000001011001`
- Majority-to-mode Hamming distance: **0**
- Mean pairwise Hamming distance: **41.971765**

## Descriptive pair diagnostics

| Radius | Observed pairs |
|---:|---:|
| 0 | 1 |\n| 1 | 2 |\n| 20 | 52 |\n| 30 | 136 |\n
Pair counts are descriptive only. Pair events are dependent, so no Poisson p-values are reported.

## Provenance

- Job: `c902a6a1-0e91-48cf-b5ba-44831fcc7726`
- Device: `Helios-1`
- Source QASM SHA-256: `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`
- Submitted QIR SHA-256: `a25a9a74e2aa99c4f76250448b4721511a5d8f01bc4d70db1f45d4a3c41ab465`

The exact raw provider payload is preserved unchanged.
