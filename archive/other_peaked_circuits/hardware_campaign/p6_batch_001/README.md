# P6 Batch 001 — gated two-stage Helios campaign

This directory is the empty-but-prepared campaign record for a sequential P6
Helios-1 experiment. Only the 100-shot discovery job may be submitted first.
The workflow must stop after retrieval and analysis; the second 100-shot job
requires an explicit user go-ahead after the candidate report is reviewed.
There is no automatic confirmation submission.

## Planned records

- [`job_records/discovery.json`](job_records/discovery.json)
- [`job_records/confirmation.json`](job_records/confirmation.json)
- [`protocol.json`](protocol.json)

The confirmation record is intentionally not executable until discovery has
been analyzed and the candidate has been frozen.

Use the templates to record the exact provider values after submission and
retrieval. Never replace `null` with an estimate for a provider-generated field.
Use `not_recorded` where the provider or local runner supplies no value.

## Source and artifact lock

- Source: `results/hardware/p6_helios_50shot_20260829/source.qasm`
- Source SHA-256: `206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4`
- Bitcode: `results/hardware/p6_helios_50shot_20260829/submitted.qir.bc`
- Bitcode SHA-256: `0109765b16777c76347857cf91860cd99f7ad6c42ae5a7a991399e484a16f155`
- Backend: `Helios-1`

The earlier 50-shot P6 job record is not part of this campaign: it was rejected
before queueing because its max-cost exceeded available credits, and it
returned no shots.

## After each job

Preserve the raw provider output unchanged, then add backend/job/result refs,
status, requested and returned shots, cost, all provider timestamps, raw-result
hash, canonical-shot hash, and analysis manifest. Potential framing anomalies
must be repaired only in a derived artifact with the raw parent and exclusion
rule recorded.

## Mandatory operator gate

After discovery retrieval, report the top candidate, method agreement, stability
diagnostics, and comparison with the existing P6 solution hypotheses. Do not
submit confirmation while this report is pending. The operator must explicitly
approve the frozen candidate and the second 100-shot spend; otherwise the
campaign ends after discovery.
