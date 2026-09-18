# P11 HQAP unscrambler report

## Decision: P9 Gate A NO-GO

The optimized matcher has a large advantage over fixed random permutations,
but that is not a fair optimized-null significance test because relabeling
does not change the optimum. The fair mismatched-window and shuffled-order
controls are retained. More importantly, the recovered permutations are
unstable across neighboring windows: pairwise agreement is
`0.0179` for `[64,128,256]`
and `0.0238` for the larger
`[256,512,768]` refinement. Mismatched-window and shuffled-order controls are
recorded in the corresponding summary records.
An independent layer-index analysis over `[8,16,32]` layers also gives only
`0.0179` agreement.
The ordered-edge sequence matcher reaches only about
`3.26` sigma against
fair shuffled-order controls in this bounded search, with neighboring-window
agreement `0.0179`. Its
best mismatched-window scores are comparable to the mirrored scores, so it
does not rescue Gate A.
Repeating the ordered-edge test after bounded P9 split/inverse and
line-routing preprocessing produces isolated high scores, but routed mapping
stability is only
`0.0179` and the best
routed mismatched-prefix score is comparable to the best mirrored score. This
is treated as routing-induced local structure, not a recovered correspondence.
The optional P9 top-K sparse-state ladder completed only the 2^12 and 2^14
retained-state runs; both had zero probability on the supervised P9 target.
The 2^16 run hit its hard 20-second bound without reaching the end of the
circuit, so the sparse branch was stopped and no P11 proposal was made.
The continuous-unitary DTW matcher reaches only
`1.44` sigma against
shuffled controls, with mapping stability
`0.0417`; its
mismatched-window scores are equal to or higher than the mirrored scores.
The finite-horizon tracker over beam widths `[8,16,32]` also shows no
advantage over shuffled paths: the best path z-score is
`0.73`, while consecutive
permutation agreement remains at most
`0.0742`.
The local-unitary variant reaches optimizer scores around 0.77-0.86, but its
fixed-center permutation agreement is only `0.1310` and its
random-permutation baseline has the same optimization-invariance limitation.

This fails the required conjunction of calibrated signal and stable
correspondence. The optimizer advantage is therefore not treated as evidence
of a usable latent mapping.
P11 structural recovery and all downstream reduction/simulation were not run.

## Components implemented and tested

- QASM event extraction with temporal layers and 2q indices.
- Unary temporal fingerprints and compatibility matrices.
- Hungarian assignment, spectral graph matching, bounded transposition
  refinement, and null controls.
- Ordered temporal edge-stream matching with fair shuffled-order controls.
- Construction-aware P9 split/inverse plus bounded line-routing diagnostic.
- P9-only top-K sparse-state ladder with explicit timeout and no-signal stop.
- Continuous one-qubit unitary sequence alignment with DTW null controls.
- Finite-horizon beam tracking over time-dependent permutation states.
- Finite-horizon permutation beam tracker.
- Small-patch unitary equivalence and phase-insensitive process similarity.
- Exact adjacent inverse cancellation with provenance.
- Historical unswap aggregate audit; pair identities were unavailable, so no
  pair-level prior was fabricated.

## Provenance

P9 SHA256: `cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35`

P11 SHA256: `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`

P11 answer contamination: **none**. Existing `results/p11_diagnosis`,
`results/p11_research`, and `results/p11_distillation` were not overwritten.
