# P11 final classical campaign report

## Final verdict

`P9_METHODS_EXHAUSTED`.

No remaining tested classical attack with a credible mechanism and tractable
resource profile succeeded on this M3 Pro / 36 GB campaign. P11 remained
blind: it was not processed, no answer was inspected, and no candidate was
generated.

## Principal unresolved branch

The fixed P9 panel contains 60 dependency-aware patches: 40 q=3 and 20 q=4,
with 2, 3, 4, 5, and 6 entanglers represented. BQSKit 1.2.1 exact synthesis
and a SciPy arbitrary-1q/fixed-CZ numerical fallback were both exercised. The
virtual permutation ledger enumerated all 6 q=3 and 24 q=4 output orders.

Only two exact reductions were verified (2/60, 3 fewer 2q updates out of 170),
below the 5% weak-go and 15% panel-cost thresholds. Two additional numerical
patches met 1e-6 but not 1e-8; no approximate global P9 rewrite was accepted.

## Independent paths

- PyZX exact graph rewriting completed on P9. It reduced the transpiled
  `rz/sx/x/cx` representation from 3,834 to 1,878 two-qubit gates. Because
  basis conversion expands the original 1,917 `rzz` gates, this is only about
  2% relative to the original entangler count and did not pass the compiler
  gate.
- QCEC passed equivalent/non-equivalent local smoke tests. Whole-P9 checking
  was bounded at six minutes and stopped at about 3.56 GB RSS; this is
  recorded as a technical limitation, not a scientific no-go.
- DDSIM timed out on the first 100-two-qubit P9 prefix at 60 seconds, so no
  larger prefixes or P11 run was attempted.
- Quimb `CircuitPermMPS` completed the P9 max-bond-128, cutoff-1e-4, 1,000-
  sample pilot in 596.7 seconds. The most common bitstring occurred once;
  there was no P9 peak signal.
- The bounded projected finite-horizon beam controller ran widths 8/16 and
  depths 2/4. Its finalists were not sent to the MPO because the available
  production runner has no virtual-permutation schedule injection boundary;
  that limitation is explicitly recorded.

All package installs, smoke tests, watchdogs, hashes, and row-level synthesis
results are preserved under `results/p11_final_campaign/`.

Final quality checks: 133 tests passed, all new campaign files passed Ruff,
27 campaign artifact checksums were verified, and no heavy campaign subprocess
remains.
