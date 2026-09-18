# P12 timing record

Job: `d5cba0df-a7aa-459e-ac51-8092645c059f`

| Quantity | Value | Source/qualification |
|---|---:|---|
| Submitted | 2026-08-25T11:40:09.466000Z | Nexus `JobStatus` |
| Queued | 2026-08-25T11:40:22.578457Z | Nexus `JobStatus` |
| Outer running | 2026-08-25T11:47:09.582787Z | Nexus `JobStatus` |
| Completed | 2026-08-25T12:56:30.438377Z | Nexus `JobStatus` |
| Submitted-to-completed | 4,580.972377 s (76m 20.972s) | Provider wall-clock elapsed |
| Outer running-to-completed | 4,160.855590 s (69m 20.856s) | Provider running duration |
| Nested result-item runtime | 237.588 s | Separate nested status field |
| Classical analysis wall time | 0.010313208 s | Measured by `time.perf_counter` for input loading, validation, counts, and four deterministic recovery methods |

For a tracker, report the UTC timestamps and label the chosen duration as
“submitted-to-completed wall-clock elapsed” or “provider running duration.” Do
not call either value gate execution time unless Quantinuum defines that field
explicitly.

The classical timing excludes Python interpreter startup, plotting, provider
queue time, and provider execution. The source timing record is preserved at
[`classical/batch_001_timing.md`](classical/batch_001_timing.md).
