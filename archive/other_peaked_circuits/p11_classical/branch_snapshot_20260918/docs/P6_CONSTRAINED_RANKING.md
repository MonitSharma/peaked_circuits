# P6 score-constrained ranking

`scripts/p6_constrained_rank.py` enforces all recorded overlap scores as
hard binary constraints and uses the D128 and loose-cutoff D512 per-bit
marginals only as soft log-likelihood priors.

The run generated 117 distinct feasible strings using 11 D128/D512 mixture
weights plus randomized tie-breaking. The combined-prior leader was:

`00011111111100100011100110100000110100110101011000000110110110`

with combined log-likelihood `-35.3916`. It satisfies every recorded score,
but the second-ranked string is only `0.0244` log-likelihood units behind it.
The D128-only and D512-only leaders are different strings, so the ranking is
strongly prior-dependent. This is a hypothesis ranking, not evidence that the
leader is the true P6 answer.

The first combined-prior leader was subsequently tested and scored only
`30/62`; that result is now included as the tenth hard constraint. The updated
ranking is in `results/p6_constrained_rank.json`.
