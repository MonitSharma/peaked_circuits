# P5/P6/P8 Classical Recovery Plan

> **Planning snapshot; superseded 2026-08-31.** Keep this document for the
> original protocol and safety gates. Do not treat its priority ordering or
> untested-method language as current; see
> [P6_P8_REASSESSMENT_20260831.md](P6_P8_REASSESSMENT_20260831.md).

This is an answer-blind, local-only recovery campaign. It never submits jobs,
retrieves challenge answers, or treats an approximate tensor-network peak as a
verified solution.

P8 is first because its sparse iSWAP-heavy geometry is suitable for
geometry-aware tensor methods. P6 follows because its weighted backbone and
possible mirror/permutation structure are targeted before MPS scaling. P5 is
third because its dense graph makes generic bond scaling poor value.

Finite-width beam search is heuristic. Best-first MPS decoding reports
certification only when the normalized right-canonical completion-mass bound
closes. Retained norm is `retained_norm_proxy`, never exact fidelity.

Safety: one heavy process, four numerical threads, preferred niceness 10, soft
RSS 20 GiB, hard process-tree RSS 24 GiB, swap-growth abort 2 GiB. D=1024 and
D=2048 require measured promotion evidence; D=4096 is never automatic.

Use the dry-run first and inspect `CAMPAIGN_STATE.json`, manifests, termination
artifacts, and `NIGHT_SUMMARY.json`. Without independent method-family
agreement, a candidate is at most provisional.
