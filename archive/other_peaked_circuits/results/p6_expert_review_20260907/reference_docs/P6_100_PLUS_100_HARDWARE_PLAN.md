# P6 Helios-1 sequential, gated 100+100 hardware plan

Status: prepared for execution after HQC refresh. No jobs are submitted by
this plan.

## Objective

Test whether P6 (`P6_titan_pinnacle`) produces a reproducible, recoverable
62-bit structure on all-to-all Quantinuum Helios-1 hardware after the retained
classical methods failed to produce a defensible candidate.

## Frozen run design

| Stage | Shots | Estimated HQC | Suggested max cost | Purpose |
|---|---:|---:|---:|---|
| Discovery | 100 | 857 | 900 | Generate and freeze a candidate target-blind |
| Confirmation | 100 | 857 | 900 | Test only the candidate frozen from discovery, after explicit approval |
| Total | 200 | 1,714 | 1,800 combined | Two independent job records |

The estimates are provider cost-confidence results at 95% confidence, not
guaranteed billing caps. A cap below the estimate can cause a pre-queue
rejection, as happened in the earlier 50-shot attempt. Do not bypass the cap.
If fewer than approximately 1,800 HQC are available, stop after discovery or
use a pre-declared lower-shot plan; do not submit an uncapped 200-shot job.

## Submission procedure — discovery only at first

1. Confirm the exact target is `Helios-1` hardware, not `Helios-1SC` or
   `Helios-1E`.
2. Confirm the source SHA-256 is
   `206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4` and the
   prepared bitcode SHA-256 is
   `0109765b16777c76347857cf91860cd99f7ad6c42ae5a7a991399e484a16f155`.
3. Submit the discovery job as `p6_physical_discovery_100` with 100 shots and
   a 900 HQC cap.
4. Save the complete job ID, artifact references, timestamps, status, cost,
   and raw result in `hardware_campaign/p6_batch_001/job_records/discovery.json`.
5. Retrieve and preserve the raw result exactly. Do not analyze by truncating
   an unexpected provider framing or by silently reversing bits.
6. Stop. Retrieve the first 100 shots and preserve them unchanged.
7. Run the target-blind discovery analysis and produce the candidate report.
   Compare the resulting candidates with the existing P6 hypotheses only after
   the blind analysis is complete. Freeze the top candidate and its hash in the
   discovery record.
8. Wait for explicit user approval naming the frozen candidate and authorizing
   the second 100-shot spend. Do not submit confirmation automatically or in
   the same command as discovery.
9. Only after that approval, submit `p6_physical_confirmation_100` with the
   same source, bitcode, target, and 100-shot/cap settings. Save its complete
   metadata in `confirmation.json`, then score the frozen discovery candidate
   on confirmation shots only.

## Discovery analysis

Compute and preserve, without external target information:

- exact-string multiplicities and descriptive pair counts;
- most-frequent string;
- weighted observed medoid;
- cluster consensus;
- coordinate-wise majority as a diagnostic, not an authority;
- split-half/bootstrap stability;
- Hamming-distance distribution;
- all candidate strings and their method provenance.

Do not use the existing externally scored 30/62–40/62 candidate list to steer
or select the discovery candidate. It may be compared after the blind analysis
as post-hoc context only.

For a discovery candidate to be promoted, at least two of the three robust
methods (most-frequent, weighted medoid, cluster consensus) should agree within
2 bits and the result should be retained with its exact method outputs. If they
do not, mark discovery as `NO_STABLE_CANDIDATE`; do not force a winner.

The discovery report must include the top candidate, every method candidate,
method agreement, stability diagnostics, and post-blind overlaps against the
existing P6 solution hypotheses. Those overlaps are comparison context only;
they must not alter the frozen candidate.

## Confirmation endpoints

The candidate is fixed before the second job. Use the second 100 shots only for
confirmation:

- exact recurrence count of the frozen candidate;
- number of shots at Hamming distance ≤15 from it;
- median and lower-tail Hamming distances;
- independent bitwise agreement and raw framing checks.

Radius 15 is frozen for 62 bits. Under a uniform null,

```text
P(distance <= 15) = 2.889186e-5
E[count in 100 shots] = 0.002889
```

Suggested interpretation:

| Confirmation result | Interpretation |
|---|---|
| ≥1 exact hit | Strong fixed-candidate recurrence; preserve and externally verify later |
| ≥3 shots within radius 15 | Strong approximate recurrence; uniform-null tail is approximately `3.9e-9` for 100 shots |
| 1–2 radius-15 shots, no exact hit | Directional but insufficient; do not call solved |
| 0 exact and 0 radius-15 shots | No confirmation of the discovery candidate |

The exact and radius-15 outcomes are co-primary. All other diagnostics are
secondary. These thresholds are fixed before the discovery job.

## Claim boundary

Even a successful confirmation establishes hardware recurrence/recovery, not
quantum advantage. Any tracker or known-answer scoring happens only after raw
data, blind analysis, candidate freeze, and confirmation analysis are complete,
and is saved as a separate external-verification record.
