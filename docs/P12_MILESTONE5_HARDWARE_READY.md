# P12 Milestone 5: hardware-campaign readiness

Status: **READY_FOR_EXPLICITLY_AUTHORIZED_HARDWARE_RUN** after the campaign artifacts are committed.

This milestone prepares a resumable physical-campaign boundary. It does not submit Helios-1 hardware work and does not submit Helios-1E emulator work. The repository remains target-blind: `external_target_scored=false` and no hidden target is read.

## Frozen identity

- Circuit: `peaked_circuit_P12_Hqap_98x2457`, 98 qubits
- Source SHA-256: `868ff86a396f86a8cbca48f7127e49c4c4f951a5a955295e5010a92b76be961d`
- QIR text SHA-256: `c003298ea5c57f963f7f9bf5ca4c94a38fc76db10582a5cc859c621ad358c820`
- QIR bitcode SHA-256: `c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`
- Syntax evidence: Helios-1SC passed; physical Helios-1 was not submitted.

## Campaign policy

The monthly budget is 3,000 HQC. The fresh 400-shot estimate is 2,742 HQC. The operational cap is derived at runtime as `min(3,000-50, estimate+100)`, yielding 2,842 HQC for this estimate. The 50-HQC reserve is never allocated.

`hardware-preflight` and `hardware-submit --dry-run` are safe. A real submission requires the exact target, frozen hashes, fresh cost evidence, `P12_ENABLE_PHYSICAL_HELIOS=1`, `--execute-hardware`, the confirmation phrase, and interactive typed confirmation. No such authorization was supplied in this milestone.

## Evidence

- Campaign state: [`hardware_campaign/campaign_state.json`](../hardware_campaign/campaign_state.json)
- Batch-001 preflight: [`hardware_campaign/batch_001/preflight/preflight.json`](../hardware_campaign/batch_001/preflight/preflight.json)
- Dry-run manifest: `results/manifests/20260821T020307Z-d1b2ee72.json`
- Readiness report: [`results/hardware_readiness_report.json`](../results/hardware_readiness_report.json)

Required final invariants: `NO_HARDWARE_JOB_SUBMITTED`, `NO_EMULATOR_JOB_SUBMITTED_IN_THIS_GOAL`, and `external_target_scored=false`.
