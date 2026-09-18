# P5/P6 Helios-1 50-shot submissions

Both jobs were submitted from `p12_quantum` after fresh provider costing, but
the provider rejected them before queueing because the requested maximum costs
exceeded the credits available to the authenticated Nexus account.

| Circuit | Shots | Estimate (95%) | Requested cap | Job | Final status |
|---|---:|---:|---:|---|---|
| P5 | 50 | 237 HQC | 300 HQC | `af68d5a2-44f5-4465-8f79-62642cbc5380` | `ERROR` |
| P6 | 50 | 431 HQC | 500 HQC | `cd5d0823-988a-4b35-93ca-419125c9df97` | `ERROR` |

Provider error for both jobs: `Job max-cost exceeds available credits`
(`code: 1002`). No shots ran and no HQC was charged. The displayed account
balance should be reconciled with the authenticated Nexus account/workspace
before retrying. Retrying with a cap below the provider estimate would not be
a safe substitute.
