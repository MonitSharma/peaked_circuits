# P11 final classical campaign

This campaign is P9-calibrated and P11-blind. It reopens only the credible
remaining paths that were previously untested: installed BQSKit/PyZX/QCEC/
DDSIM/Quimb validation, dependency-aware local patches, q=3/q=4 exact and
bounded numerical synthesis, permutation-aware replacement, and the published
CircuitPermMPS loose end.

The fixed P9 panel is frozen in
`results/p11_final_campaign/P9_PATCH_PANEL.json` before synthesis. A method can
be transferred to P11 only after it passes both the local reduction gate and
the known P9 56/56 peak-recovery gate. Missing packages are technical results,
not scientific no-go results; the numerical fallback is required whenever
BQSKit cannot execute.
