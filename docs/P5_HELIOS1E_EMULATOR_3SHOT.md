# P5 Helios-1E emulator pipeline test

Status: submitted and provider-reported `RUNNING`; no hardware execution.

- Branch: `p12_quantum`
- Circuit: `/Users/monitsharma/Downloads/P5_granite_summit.qasm`
- Target: `Helios-1E` emulator
- Requested shots: **3**
- Maximum cost: **100 HQC**
- Job name: `p5-helios1e-emulator-3-20260829`
- Nexus job: `58332d6a-56dd-408c-88bf-c7bdade95325`
- Nexus project: `19ca0391-b7f1-4cb1-b001-4a60e2552ee9`
- QIR artifact: `cc530fb0-93bb-46ab-a8a8-b6f71864a5ba`
- Source QASM SHA-256: `cee80b7bcdb61c87729853adcfd80e0aa3a20da54e29127eef180cfa65e6c386`
- Submitted QIR SHA-256: `6ad242faa0facbf8184164ff5846912aa79c5c3aaece08cbdb6a9304799fd58b`
- Submitted bitcode SHA-256: `c21ea71e6433e5d95d1b8494e5a98675717a96e61a41b4e529353c1b99b0ad9a`

The explicit 44-qubit `HeliosEmulatorConfig` used an MPS simulator and
`NoErrorModel`. The run is a pipeline/framing test only; its samples must not
be treated as a P5 solution or quantum-advantage evidence. The provider
currently reports 5 HQC for the running job, within the 100-HQC ceiling.

The submission metadata, source QASM, measured QIR, and bitcode are preserved
under `results/emulator/p5_helios1e_3shot_20260829/`. Retrieval remains pending.
