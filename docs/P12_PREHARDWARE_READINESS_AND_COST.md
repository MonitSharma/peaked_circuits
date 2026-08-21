# P12 pre-hardware syntax and cost evidence

Fresh provider evidence was obtained on 2026-08-20 UTC for the frozen P12 QIR.

## Frozen identity

- Circuit: `peaked_circuit_P12_Hqap_98x2457`
- Source QASM SHA-256: `868ff86a396f86a8cbca48f7127e49c4c4f951a5a955295e5010a92b76be961d`
- QIR text SHA-256: `c003298ea5c57f963f7f9bf5ca4c94a38fc76db10582a5cc859c621ad358c820`
- QIR bitcode SHA-256: `c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`

## Helios-1SC syntax check

Status: **passed** (`COMPLETED`)

- Target: `Helios-1SC`
- Job: `92154b08-1e0a-4b82-a483-b6d59938b937`
- Project: `19ca0391-b7f1-4cb1-b001-4a60e2552ee9`
- Uploaded QIR artifact: `6458af03-dd24-4810-b5e8-1623a54cc12f`
- HQCs spent: `0`
- Scientific shots: `0`

The syntax-check result is provider-validity evidence only; it is not a scientific P12 sample.

## Fresh HQC cost ladder

API: `qnexus.qir.cost_confidence` with provider costing system `Helios-1`. Confidence was 95 for every estimate. The CLI’s `Helios-1E` label denotes the existing cost-evidence guard; no emulator execution occurred.

| Shots | Predicted HQC | Confidence | Fits 3000 HQC? | Headroom |
|---:|---:|---:|:---:|---:|
| 1 | 12 | 95 | yes | 2988 |
| 10 | 74 | 95 | yes | 2926 |
| 20 | 142 | 95 | yes | 2858 |
| 50 | 348 | 95 | yes | 2652 |
| 100 | 690 | 95 | yes | 2310 |
| 250 | 1716 | 95 | yes | 1284 |
| 350 | 2400 | 95 | yes | 600 |
| 375 | 2571 | 95 | yes | 429 |
| 400 | 2742 | 95 | yes | 258 |
| 410 | 2811 | 95 | yes | 189 |
| 420 | 2879 | 95 | yes | 121 |
| 425 | 2913 | 95 | yes | 87 |
| 430 | 2948 | 95 | yes | 52 |
| 500 | 3427 | 95 | no | -427 |
| 1000 | 6848 | 95 | no | -3848 |
| 2000 | 13690 | 95 | no | -10690 |

## Future monthly recommendation

- Largest tested count under 3,000 HQC: **430 shots**.
- Recommended operational count: **400 shots/month**.
- Fresh prediction: **2742 HQC** at 400 shots.
- Operational `max_cost` is derived at runtime as prediction + 100 HQC allowance,
  capped at 3000 - 50 HQC reserve: **2842 HQC** for this estimate.
- Estimated cumulative campaign duration at 400 shots/month:
  - 800 shots: 2 months
  - 1200 shots: 3 months
  - 1600 shots: 4 months
  - 2000 shots: 5 months

These are planning values only. No physical hardware batch was submitted. The Milestone 5
preflight and dry-run artifacts are under `hardware_campaign/`.

## Safety record

- Helios-1E executions this goal: **0**
- Helios-1 physical executions this goal: **0**
- Physical HQCs spent this goal: **0**
- Only Helios-1SC syntax checking and provider costing were performed.

The machine-readable source for the complete ladder is `results/nexus/cost/p12_cost.json`.
