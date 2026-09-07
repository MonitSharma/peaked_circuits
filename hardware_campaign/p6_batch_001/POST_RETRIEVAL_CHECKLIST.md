# P6 post-submission and post-retrieval checklist

This checklist is offline documentation. It does not poll or submit a provider
job by itself.

## Immediately after submission

- [ ] Confirm target is exactly `Helios-1`.
- [ ] Record provider `job_id`, result/artifact references, job name, and
      submission timestamp in the appropriate JSON record.
- [ ] Record requested shots and max-cost exactly as submitted.
- [ ] Confirm source and bitcode SHA-256 values match `protocol.json`.
- [ ] Record any provider acceptance, queue, or rejection message verbatim.

## When the job finishes

- [ ] Record final status, completion timestamp, reported HQC, queue time,
      running time, and any provider execution-time field.
- [ ] Download the raw result once and preserve it byte-for-byte.
- [ ] Compute and record the raw-result SHA-256.
- [ ] Inspect framing and returned shot count; do not silently truncate, pad,
      reverse, or reorder records.
- [ ] If a framing repair is necessary, write a separate derived artifact with
      raw parent hash, exact repair rule, excluded records, and output hash.
- [ ] Normalize to 62-bit canonical strings using the saved mapping.
- [ ] Save canonical shots, counts, manifest, and checksums.
- [ ] Run discovery analysis without hidden-target or external-overlap input.

## Before confirmation submission

- [ ] Freeze the discovery candidate and candidate hash in
      `job_records/discovery.json`.
- [ ] Record the methods that agree and the stability diagnostics.
- [ ] Set `candidate_frozen_before_confirmation` to `true` in
      `job_records/confirmation.json`.
- [ ] Copy the frozen candidate hash into the confirmation analysis input.
- [ ] Do not alter the radius-15 or exact-recurrence decision rules.

## After confirmation retrieval

- [ ] Preserve confirmation raw and canonical artifacts separately from
      discovery artifacts.
- [ ] Score the frozen discovery candidate only on confirmation shots.
- [ ] Record exact hits, radius-15 hits, Hamming summaries, and the predeclared
      decision.
- [ ] Only after all blind analysis is complete, attach any external tracker or
      known-answer score as a separate post-hoc verification record.
- [ ] Keep quantum-advantage interpretation separate from recovery statistics.
