# P5/P6/P8 Recovery V2 Report

> **Historical snapshot (2026-08-29).** This report preserves the original
> V2 campaign chronology. It is superseded as a live status summary by
> [P6_P8_REASSESSMENT_20260831.md](P6_P8_REASSESSMENT_20260831.md), which adds
> the later P6/P8 MPS, structural, tail-materialization, and runtime results.

## Repository and validation

The authoritative branch is `p11_classical`. The evidence checkpoint is commit
`358044e`; the follow-up framework and bounded P6/P8 diagnostics are committed after this report. The P5, P6,
and P8 input hashes are recorded in `results/p5_p6_p8_recovery/SHA256SUMS`.
The non-hardware suite passed 201 tests with one Quimb efficiency warning at
the time of this snapshot. The current suite passes 202 tests; see the current
reassessment for the runtime fix and exact verification command.

The official local MPO checkout is pinned by provenance to commit
`b1bed0a5621f99d95ca7834a82d72dfd5db46cf4`. Its P9 positive-control run passes,
and the explicit logical q0-first/portal mapping layer is tested and recorded in
`controls/p9/P9_BIT_ORDER_CALIBRATION.json`.

## Current scientific status

P5 retains a meaningful partial signal from the inherited sampled MettleQ run.
The new answer-blind reliability artifact has 35 `LIKELY` and 9 `UNCERTAIN`
bits, but only one method family is currently usable. No bit is classified
`LOCKED`, and no joint refinement has been promoted. The candidate was frozen
before evaluation in `P5/freezes/P5_CANDIDATE_FREEZE.json`; no target answer,
overlap, portal feedback, or post-hoc score was read.
One independent spectral-order D128 MPS rung was then run under a 10-minute
cap. It completed in 224 seconds at 236 MB peak RSS, but its retained norm proxy
was `3.64e-26` and it emitted no MAP record, so it was rejected and not counted
as a valid consensus family.
The calibrated full MPO/unswapping path then completed all 902 consolidated
gates in 295 seconds, with seven unswap cycles, peak bond 128, final bond 26,
and peak RSS 0.836 GiB. A 256-sample beam extraction produced an 8-entry
top-k set and was frozen before evaluation. Its top candidate differs from the
MettleQ freeze by Hamming distance 22, so P5 is currently a promising candidate
family rather than cross-method convergence.
An independent cutoff-0.01 repeat also completed all 902 gates, but its frozen
candidate differs by Hamming distance 26 from the cutoff-0.005 MPO candidate;
this is recorded as cutoff-sensitive and is not counted as convergence.

P6 has a useful weighted interaction-structure probe and a P9-calibrated MPO
path. Existing prefix and full-D128 runs are diagnostics only: they consumed
work and unswapping telemetry but did not produce a decoded target candidate.
The full D128 compression completed 2,593 work gates and ten unswap cycles, but
a sampled follow-up reached only 2,004 gates before bounded interruption and
never reached extraction; its state is recorded as `NONCONVERGED` with no
promoted candidate.
The inherited 34/62 candidate is not used as a prior.
The new weighted ordering analysis gives routing proxies of 72,004 (identity),
51,807 (spectral), and 42,770 (heavy-greedy); this is a structural scheduling
signal only and has not been converted into a candidate.
The faithful P9-calibrated D512/cutoff-0.0006 MPO attempt stalled at 86 work
gates under the solver's routing-only no-progress guard. Raising the guard to
20 cycles reached 102 work gates before bounded interruption and still emitted
no candidate. A weighted heavy-greedy CircuitPermMPS fallback at D128 then
completed in 300 seconds, but its retained norm proxy was `1.18e-30`, its
maximum bond reached only 8, and it emitted no MAP record; it is rejected as a
recovery route. P6 therefore has no new candidate beyond the inherited string.
Following the solver's diagnostic suggestion, a separate D512 run with the
no-progress abort disabled was observed under the same 24-GiB RSS and bounded
wall guards. It advanced only 26 gates in 128 seconds (the checkpoint recorded
35 gates), then was interrupted because the extrapolated extraction time was
multi-hour. It produced no candidate and is classified `RESOURCE_NO_GO`.
The earlier full-D128 diagnostic was also retried with sampling enabled in its
validated isolated environment. It plateaued at 122/2,593 gates after 201
seconds and was interrupted; because sampling occurs only after compression,
this does not reveal a missed candidate and is recorded as another
`RESOURCE_NO_GO`.

P8 has sparse degree-limited geometry, but the existing simple-update geometry
diagnostics are unstable and PEPO remains quarantined until positivity and exact
controls pass. No P8 production candidate is promoted.
The weighted recursive TTN topology covers all 40 P8 qubits, and a 10-qubit
iSWAP-grid exact control passes its control-only decoder. This is not sufficient
to promote a target TTN run without environment-aware approximation validation.
A positivity-checked pairwise graph-BP decoder also passes a 10-qubit
tree-factorized control in 10 iterations. It remains unpromoted because target
pairwise environment factors have not been derived and validated.
The first target D4/max-distance-2 environment attempt found 3 negative joint
factors and was rejected. A radius-3 retry was stopped after 351 seconds at
about 5.9 GiB RSS without completing; it emitted no candidate and is recorded as
non-converged.
An explicit Fréchet-bounded positivity projection made the radius-2 factors
usable for a diagnostic BP run, which converged in 21 iterations. However, it
changed three factors, with maximum absolute `p00` correction 0.157, so the
result is rejected rather than promoted.
The calibrated P8 MPO route was also exercised at D512/cutoff-0.0006 and an
answer-blind escalation at D1024/cutoff-0.0001. They reached 785/808 and
774/808 work gates respectively, but stopped without sampling or decoding;
neither produced a candidate. These outcomes are recorded in
`P8/mpo/STATE_calibrated_escalation.json`.
A separate spectral-order D128 MPS control completed in 96 seconds, reached
the bond cap, and retained only `1.01e-21` of norm proxy without emitting a MAP
record. It is rejected alongside the earlier identity-order MPS result; no
P8 candidate is promoted.
The available mirrored-TNO implementation was then given a bounded D4/cutoff
0.01 feasibility probe. The solver environment lacked its optional `tnag`
module, while the main environment timed out after 133 seconds before the
core completed. It emitted no candidate and is recorded as `RESOURCE_NO_GO`.
Finally, a target-capable weighted TTN simulator was validated on an exact
two-qubit control and run on P8 at D2, D4, and D8. It completed in 46–131
seconds under 0.94 GiB RSS, but the three frozen candidates differ pairwise by
15, 24, and 17 bits. Their discarded-weight proxies are large, so the TTN
family is rejected as unstable and none is externally evaluated or promoted.

## Conclusion and next step

At the time of this snapshot, labels were: P5 `PROMISING_CANDIDATE_FAMILY`
(not converged); P6 `NONCONVERGED` with no new candidate; P8
`CURRENT_METHODS_EXHAUSTED` for the then-tested MPS/simple-update/MPO/TNO
routes. The target-capable
weighted TTN implementation passes its exact small control, but its P8 bond
2/4/8 candidate family is unstable and is rejected. Graph-BP remains
control-only because its target environment factors failed positivity checks.
An unweighted spectral-tree D4 repeat produced a fourth candidate differing by
17/40 bits from the weighted D4 result, confirming topology sensitivity rather
than convergence. It is included in the pre-evaluation freeze and rejected.
Using positive unary/pairwise marginals extracted from the TTN, graph BP
converged at both D4 and D8, but the resulting correlated diagnostic strings
differ by 19/40 bits. They are frozen separately and rejected as unstable,
not counted as independent TTN evidence.
These are not claims of classical impossibility or exact recovery.

The following command is retained only as historical provenance; do not use it
as a blind retry. Follow the current reassessment instead:

```bash
caffeinate -i nice -n 10 env PYTHONPATH=src .venv/bin/python \
  scripts/run_peak_recovery_portfolio.py --execute --resume \
  --night-budget-hours 7 --threads 4 --rss-soft-gb 20 --rss-hard-gb 24 \
  --swap-growth-limit-gb 2 --cooldown-minutes 5
```
