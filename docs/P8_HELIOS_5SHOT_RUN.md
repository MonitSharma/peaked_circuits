# P8 Helios-1 5-shot exploratory run

Status: submitted; awaiting provider execution and retrieval.

This run follows the P11/P12 provenance procedure. The raw source QASM was
converted deterministically to measured QIR after decomposing the custom
`iswap` definition, and the source, QIR, and bitcode hashes were preserved.

## Frozen submission

- Branch: `p12_quantum`
- Circuit: `/Users/monitsharma/Downloads/P8_grid_888_iswap.qasm`
- Target: physical `Helios-1`
- Requested shots: **5**
- Maximum cost: **35 HQC**
- Job name: `p8-physical-5-20260829`
- Nexus job: `dd2089ba-1e84-4b46-b104-f848e48e4bcc`
- Nexus project: `19ca0391-b7f1-4cb1-b001-4a60e2552ee9`
- QIR artifact: `fd9fa174-23b6-4000-8c2a-c9686f53598a`
- Source QASM SHA-256: `ba42c338478fdfbc0241ec2289b3159bfde5dffc71603ac588ec0755fba1a484`
- Submitted QIR SHA-256: `ed36e11775ffb2b0009a9218ee284c614b3a55e0db01056f71a997d010c35e05`
- Submitted bitcode SHA-256: `a5c3df07b4e08db4a2a5a18c12b84d7b5c925719568ec1b837a4ec3d15bb70bf`
- Initial provider status: `SUBMITTED`

The source QASM contains 40 qubits and 888 custom `iswap` operations. The
submitted artifact contains explicit measurement of all 40 logical qubits.
The 35-HQC ceiling is a hard provider-side maximum; the provider's prior
cost-confidence estimate was 31 HQC at 5 shots.

## Retrieval commitment

When the job reaches a terminal state, preserve the provider payload, result
references, returned-shot count, reported cost, queue time, execution time,
backend metadata, and checksums before any candidate analysis. Analyze these
five shots as exploratory hardware evidence only; they cannot establish a
P8 answer or a quantum-advantage claim by themselves.
