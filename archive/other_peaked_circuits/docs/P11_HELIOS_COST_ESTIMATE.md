# P11 Helios cost estimate

Checked: 2026-08-28

The supplied `<local-user>/Downloads/P11_hqap_1999.qasm` was verified against the P11 metadata in this repository:

- Qubits: `98`
- CZ gates: `1,999`
- Source QASM SHA-256: `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`
- Locally generated QIR SHA-256: `a25a9a74e2aa99c4f76250448b4721511a5d8f01bc4d70db1f45d4a3c41ab465`

The QASM was converted to QIR locally and submitted to the provider's `Helios-1SC` costing path only:

- Requested shots: `200`
- Estimated cost: **`1118 HQC`**
- Confidence: **`95%`**
- Execution status: **costing only; no P11 emulator or hardware job submitted**

This estimate is for the exact supplied P11 circuit after the repository's deterministic QIR conversion. It is not a prediction that 200 shots will recover the hidden peak; that would require an execution and an independently specified analysis protocol.
