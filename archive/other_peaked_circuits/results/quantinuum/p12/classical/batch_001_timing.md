# Batch 001 provider timing

Source: Nexus `JobStatus` for job `d5cba0df-a7aa-459e-ac51-8092645c059f`, recorded in UTC.

- Submitted: `2026-08-25T11:40:09.466000Z`
- Queued: `2026-08-25T11:40:22.578457Z`
- Running: `2026-08-25T11:47:09.582787Z`
- Completed: `2026-08-25T12:56:30.438377Z`
- Submitted-to-completed wall-clock time: `4580.972377` seconds (`76m 20.972s`)
- Provider running-to-completed time: `4160.855590` seconds (`69m 20.856s`)

The result item's nested status reports a different running timestamp (`2026-08-25T12:52:31.893104Z`), so it implies `237.588` seconds of result-item runtime. We preserve both provider timestamps rather than choosing one silently. For a tracker, report the four UTC timestamps and label the duration as either wall-clock elapsed time or provider running duration. Do not call either value “gate execution time” unless Quantinuum defines that field explicitly.
