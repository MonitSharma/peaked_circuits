# P11 extraction investigation

Status: Phase A complete; P9 decoder gate failed at P11-comparable fidelity.
Decision: `NO_GO_MAP_DECODER`. No new P11 run is authorized by the protocol.

## Phase A: existing blind samples

The preregistered analysis used the canonical `permuted` column from the
completed 5e-3 and 4e-3 blind runs. It did not read an answer, verifier, or
other oracle. Both source sample directories remain unchanged.

- 5e-3 majority candidate versus 4e-3 majority candidate: Hamming distance 45/98.
- Majority signs agree at 53/98 positions.
- Held-out mean Hamming distances are 47.319 and 48.197, with bootstrap mean
  confidence intervals [47.056, 47.596] and [47.909, 48.471].
- Decision grade: `NO_REPRODUCIBLE_SIGNAL`.

The machine-readable artifacts are under
`results/p11_extraction/existing_samples/` and are covered by `SHA256SUMS`.

## Decoder calibration

The solver now has opt-in final-MPS decoders. `--decoder marginals` computes
one-site computational-basis marginals; `--decoder beam` runs a bounded
conditional top-K beam. The default solver behavior is unchanged.

The full P9 marginal calibration completed 1885/1885 gates without a crash.
The sampled mode matched the known P9 control target, but the one-site
marginal MAP did not, so the marginal decoder is not sufficient by itself.

A separate full P9 beam calibration at cutoff `5e-3` completed 1885/1885 gates
without a crash. At this P11-comparable fidelity:

- the random-sample mode was 29 bits from the known P9 control;
- the direct-marginal candidate was 29 bits away;
- the beam top-1 was 25 bits away, and none of the top 8 candidates matched;
- the beam probabilities were on the order of `5e-9`, indicating a highly
  diffuse approximate state rather than a recovered control peak.

The completed calibration artifacts are in the solver worktree under
`runs/p9_loose_beam_calibration_20260827/`. Because the beam decoder does not
recover P9 at the comparable loose fidelity, the protocol terminates the MAP
path here. In particular, no new P11 run and no route-replay experiment should
be started on the basis of this decoder.
