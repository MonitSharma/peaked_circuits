# P11 Helios-1 50-shot run

Status: completed and retrieved.

This run follows the P12 campaign provenance procedure: the supplied P11 QASM
was converted deterministically to QIR, the source and QIR hashes were checked,
the exact provider job and artifact references were preserved, and the raw
provider result will be retrieved without candidate-dependent filtering.

## Frozen submission

- Branch: `p12_quantum`
- Circuit: `/Users/monitsharma/Downloads/P11_hqap_1999.qasm`
- Target: `Helios-1` hardware
- Requested shots: **50**
- Maximum cost: **300 HQC**
- Job name: `p11-physical-50-20260828`
- Nexus job: `c902a6a1-0e91-48cf-b5ba-44831fcc7726`
- Nexus project: `19ca0391-b7f1-4cb1-b001-4a60e2552ee9`
- QIR artifact: `5b01c739-15ec-4892-8f93-7dd96c448eaf`
- Source QASM SHA-256: `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`
- Submitted QIR SHA-256: `a25a9a74e2aa99c4f76250448b4721511a5d8f01bc4d70db1f45d4a3c41ab465`

## Retrieved result

- Provider status: `COMPLETED`
- Requested/complete returned shots: **50/51**
- Reported cost: **282.98 HQC**
- Queue time: approximately **10,732 seconds**
- Execution time: approximately **230 seconds**
- Most frequent returned string: `01111110011011000111010110011001001001111011110000001001101101011011101111000010110011000001011001`
- Mode multiplicity: **2**
- Radius-31 cluster around the observed mode: **2 shots**

The provider fused the final five shot frames into one section. The raw payload
contains 4,998 labeled measurements, exactly 51 complete 98-bit records, so
the extraction chunks globally by the 98 measurement labels and records the
requested/returned discrepancy rather than dropping or fabricating shots.

The P11 sample does not show a strong P12-like collision/cluster structure in
this 50-shot run. See the preserved raw data and independent analysis under
`hardware_campaign/p11_batch_001/` and `results/jobs/`.

## Analysis commitment

After retrieval, preserve the provider payload, result references, backend
metadata, timestamps, reported cost, submitted QIR, and checksums. Analyze the
50 shots as an independent exploratory P11 hardware sample. Any candidate or
pattern found is recurrence/observation evidence only; it is not a
quantum-advantage claim or hidden-target verification.
