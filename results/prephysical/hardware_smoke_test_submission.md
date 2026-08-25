# Helios-1 smoke-test submission boundary

- Branch: `p12_quantum`
- Target: `Helios-1`
- Requested shots: `1`
- Maximum cost: `80 HQC`
- Deterministic provider job name: `p12-physical-smoke-20260825-1shot-125707fb`
- Project reference: `356d6543-945e-4726-9d0e-a351d87cf859`
- QIR artifact reference: `b906176d-7d0e-4528-b39d-fac72d9df604`
- Job reference: `62dd05e1-9d5b-48dc-be28-b5a41d45df21`
- Current provider status: `SUBMITTED`

The project and QIR artifact uploads completed. The initial provider execution-resource creation returned HTTP 504 (`Deadline exceeded`) before returning a job reference. A later reconciliation by the deterministic job name found the accepted job above, proving the timeout was a response/reconciliation delay rather than evidence that submission failed. The job has now completed with a provider-reported submission anomaly and an available one-shot result; see `hardware_smoke_test_result.md`. No retry was made.

Batch 001 was not touched: it remains `PLANNED`, 200 shots, with no execution job or result references.
