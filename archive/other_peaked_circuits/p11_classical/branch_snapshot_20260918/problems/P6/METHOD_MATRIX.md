# P6 classical method matrix

This is a curated closure matrix. “Closed” means the tested implementation and
resource envelope did not produce a verified blind candidate; it is not a proof
of impossibility. Positive-control results are included because they test
whether a method preserves a known peak.

| Method | Scientific hypothesis | Positive control | P6 result | Closure reason | Canonical evidence |
|---|---|---|---|---|---|
| Ordinary MPS | line-state evolution is affordable | P5/P9 controls pass in calibrated regimes | early bond/routing wall; no candidate | insufficient faithful progress | [`P6_MPO_DIAGNOSIS.md`](../../docs/P6_MPO_DIAGNOSIS.md) |
| Permutation MPS | track logical swaps classically | P8 frame exactness tests | no P6 candidate | representation alone does not remove ordering cost | [`P6_REPRESENTATION_INVESTIGATION_20260901.md`](../../docs/P6_REPRESENTATION_INVESTIGATION_20260901.md) |
| Midpoint MPO | compress the middle and unswap | P5/P9 retain peaks | D512/6e-4 stalls around 138–150 | faithful route reaches no-progress attractor | [`P6_MPO_DIAGNOSIS.md`](../../docs/P6_MPO_DIAGNOSIS.md) |
| Cutoff ladder | a middle tolerance completes faithfully | P5/P9 tolerate 1.5e-3 | 1.875e-3 and 2e-3 complete but flatten readout | completion/fidelity boundary | [`P6_REPRESENTATION_INVESTIGATION_20260901.md`](../../docs/P6_REPRESENTATION_INVESTIGATION_20260901.md) |
| Flip/routing variants | absorption order or route choice escapes | P8 flip changes endpoint | flip 2 improves some screens but no P6 peak | no complete faithful candidate | [`P6_CANDIDATE_LEDGER.md`](../../docs/P6_CANDIDATE_LEDGER.md) |
| Readout precision | lost peak may be numerical readout only | controls retain peak | high-precision materialization remains flat | information was lost during compression | [`P6_MPO_DIAGNOSIS.md`](../../docs/P6_MPO_DIAGNOSIS.md) |
| Tail/materialization | finish only a small residual tail | P8 tail gives validated 40/40 | P6 faithful runs stall far too early; loose endpoint is flat | no useful late-state handoff | [`CANONICAL.md`](CANONICAL.md) |
| Route quality/lookahead | better routing score finds absorbable path | P8 route screens diagnose attractor | pair lookahead and route variants do not promote | cost or no escape | [`P6_CANDIDATE_LEDGER.md`](../../docs/P6_CANDIDATE_LEDGER.md) |
| PyZX | exact graph rewriting reduces contraction | P9 reduction is useful as control | no useful P6 MPO rescue | reduction did not yield a tractable faithful route | [`P6_REPRESENTATION_INVESTIGATION_20260901.md`](../../docs/P6_REPRESENTATION_INVESTIGATION_20260901.md) |
| CAMPS | Clifford-plus-residual representation is sparse | P5/P9 control screens | nullity saturates; no small residual | screening proxy gives no opening | [`P6_CAMPS_FEASIBILITY.md`](../../docs/P6_CAMPS_FEASIBILITY.md) |
| KAK/Weyl | two-qubit local invariants reveal reusable structure | control comparisons retained | oracle/structural diagnostics, no blind candidate | not a complete reconstruction | [`P6_KAK_ORACLE_RESULTS.md`](../../docs/P6_KAK_ORACLE_RESULTS.md) |
| Structural reconstruction | local patches expose hidden circuit structure | P9/patch controls | local matches, no full candidate | neighborhood does not constrain globally | [`P6_PATCH_INVARIANT_SCREEN.md`](../../docs/P6_PATCH_INVARIANT_SCREEN.md) |
| Pauli propagation | Heisenberg observables remain sparse | P5 is the control | support growth defeats sparse tracking | fails control-informed scalability test | [`P6_PAULI_PROPAGATION_FEASIBILITY.md`](../../docs/P6_PAULI_PROPAGATION_FEASIBILITY.md) |
| SOP/rank-width | path-variable graph has manageable width | controls establish scale | cut-rank scales with qubit count | heuristic width is too large | [`P6_SOP_RANK_WIDTH_FEASIBILITY.md`](../../docs/P6_SOP_RANK_WIDTH_FEASIBILITY.md) |
| Patch invariants | U/U† patches identify target bits | P9 is degenerate control | invariants underconstrain P6 | no discriminating candidate family | [`P6_PATCH_INVARIANT_SCREEN.md`](../../docs/P6_PATCH_INVARIANT_SCREEN.md) |
| Split cutoff | different tolerances on sides preserve signal | P5/P9 calibration | no verified P6 result | no defensible blind promotion | [`P6_MPO_DIAGNOSIS.md`](../../docs/P6_MPO_DIAGNOSIS.md) |
| Circuit cutting | divide long circuit into manageable pieces | controls required | bounded screens did not close bitstring | stitching cost/ambiguity remains | [`P6_CANDIDATE_LEDGER.md`](../../docs/P6_CANDIDATE_LEDGER.md) |
| Pilot-Wave sampling | diagonal-aware exact sampling avoids full state storage | bounded structural probe only; no sampling attempted | closed at planner stage: 250 source ops took 29.9 s; 500 exceeded 60 s | reference greedy SSA planner scales poorly before full P6 | [`p6_pilot_wave_probe.py`](../../scripts/p6_pilot_wave_probe.py), [`prefix250.json`](../../results/p6_pilot_wave_feasibility/prefix250.json) |
| Constrained ranking | overlap ledger can rank candidate families | explicitly post-hoc only | references are diagnostics, not generator input | oracle use prohibited for tuning | [`P6_CONSTRAINED_RANKING.md`](../../docs/P6_CONSTRAINED_RANKING.md) |

## Interpretation

The repeated pattern is a tradeoff: tighter cutoffs preserve information but
stall the router, while looser cutoffs complete but produce near-uniform
readout. This is why P6 remains unresolved despite substantial diagnostic
coverage.

Pilot-Wave is closed as a practical route under the tested implementation and
resource budget. Its planner became the bottleneck before a meaningful P6
sampling run could begin. This is a method-specific no-go, not a theorem that
P6 has no classical solution.
