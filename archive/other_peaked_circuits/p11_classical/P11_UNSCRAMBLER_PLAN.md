# P11 HQAP unscrambler plan

This branch tests explicit structural recovery of hidden HQAP correspondence:
temporal event extraction, bounded mirror-window matching, piecewise
permutation tracking, local patch equivalence, and exact-only simplification.
It deliberately does not restart the exhausted MPO, restoring-MPS, or generic
full-state experiments.

## Blindness and gates

P9 is the supervised development circuit. P11 QASM may be structurally
analyzed, but no P11 answer, submission, hardware output, emulator output, or
oracle is read. P9 Gate A requires both strong null separation and stable
mapping across neighboring windows. P11 is not entered unless that gate passes.

The bounded structural protocol used here tested unary temporal fingerprints
and spectral/edge-agreement matching over the prescribed three-window sets:
`[64, 128, 256]` and one justified larger-window refinement
`[256, 512, 768]`. An independent layer-axis test used `[8, 16, 32]`
layers, and a local-unitary test compared direct/adjoint one-qubit layers.
Random-permutation, mismatched-window, and shuffled-order controls were
retained. Random relabeling is treated only as a fixed-mapping baseline:
optimized matching scores are not incorrectly called a significance test,
because relabeling leaves the optimum invariant.

## Current decision

P9 shows large score-vs-random-null z-scores, but the recovered mappings are
not stable: neighboring-window agreement is approximately 0.02 for both
window sets. This is consistent with an underconstrained graph score rather
than a recovered latent correspondence. Gate A therefore fails and the
protocol stops before P11 structural recovery, reduction, or simulation.

Historical unswap telemetry was audited as a soft-prior source. The preserved
logs expose aggregate swap counts and cycle/side positions, but not normalized
logical pair identities, so no pair-level prior can be responsibly constructed
from those artifacts.

All historical result directories remain untouched.
