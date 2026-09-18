# P11 distillation report — bounded P9 gate result

## Decision

**P9 Gate A: NO-GO. P11 was not run.** The direct-marginal low-bond engine
recovered 36/56, 29/56, and 27/56 P9 bits at D=16, 32, and 64 respectively.
Confidence also declined from D=16 to D=64. The D=128 run was stopped after
more than twelve minutes under the resource policy because it was not showing
an improving signal; D=256 was not launched. No P11 candidate was produced.

This is a no-go for this specific low-bond MPS protocol on this machine, not a
claim that P11 is classically impossible.

## Method

The wrapper uses the local MettleQ MPS engine with complex64 tensors,
renormalized SVD splits, restoring swap routing, direct single-site Z
expectations, explicit logical-to-site mapping, checkpoint snapshots every
500-1000 operations, and process RSS telemetry. The global discarded-weight
diagnostic is reported but was not used to reject runs.

P9 was the only truth comparison. P11 remained blind: no P11 output, tracker
submission, emulator, hardware result, or leaked bitstring was consulted.

## Reproducibility

See `AUDIT.json`, `p9_distillation_ladder.csv`, `p9_bit_marginals.csv`, and
`p9_bit_stability.csv`. The engine source is
`tools/run_mps_distillation.py`; the external MettleQ checkout was pinned to
the local clone used for these runs and its package version is recorded in the
audit. The canonical P9 input hash is
`cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35`.
