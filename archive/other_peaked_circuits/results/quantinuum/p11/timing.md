# P11 timing record

Job: `c902a6a1-0e91-48cf-b5ba-44831fcc7726`

| Quantity | Value | Source/qualification |
|---|---:|---|
| Queue time | 10,732.063968 s (178m 52.064s) | Provider raw metadata |
| Hardware execution time | 229.924343 s (3m 49.924s) | Provider raw metadata |
| Queue + execution | 10,961.988311 s (3h 2m 41.988s) | Arithmetic sum; not a separately reported wall-clock field |
| Classical analysis wall time | Not recorded | No retained start/end telemetry |

Use “provider-reported execution time” for 229.924343 s. Do not call it
gate-level execution time. The separate queue time explains why the end-to-end
turnaround was much longer than the circuit execution itself.

The complete timing fields are preserved in:

- [`quantum/raw_provider_result.json`](quantum/raw_provider_result.json)
- [`classical/job_metadata.json`](classical/job_metadata.json)
- [`protocol/P11_HELIOS_50SHOT_RUN.md`](protocol/P11_HELIOS_50SHOT_RUN.md)
