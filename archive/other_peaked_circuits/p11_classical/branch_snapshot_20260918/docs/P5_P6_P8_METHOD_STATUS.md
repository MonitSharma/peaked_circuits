# P5/P6/P8 Method Status

> **Current snapshot: 2026-09-01.** The problem archive is indexed in
> [`../problems/`](../problems/). The detailed, answer-blind reassessment is
> [P6_P8_REASSESSMENT_20260831.md](P6_P8_REASSESSMENT_20260831.md). Historical
> summaries below remain useful for provenance, but they are not a claim that
> any target peak has been recovered.

| Problem | Method | Current status |
|---|---|---|
| P5 | MPS / MettleQ sampled approximation | Partial signal; one usable sampled family |
| P5 | Answer-blind ensemble reliability | Implemented; independent MPO family now frozen; no bitwise convergence |
| P5 | MPO/unswapping | Full 902-gate run and 256-sample extraction completed; frozen top-k differs from MPS by Hamming 22 |
| P6 | MPS / permutation-MPS | D64--D128 legacy runs and new annealed D128 fail retained-fidelity diagnostics; no candidate |
| P6 | Weighted structure + MPO/unswapping | `1.875e-3` and `2e-3` complete but are flat; tighter faithful settings stall; no verified candidate |
| P8 | MPS / permutation-MPS | New annealed D256 fails the calibrated fidelity gate; no candidate |
| P8 | Simple-update PEPS | Demoted; geometry diagnostics are unstable |
| P8 | PEPO | Quarantined pending positivity and exact-control validation |
| P8 | MPO controller / tail materialization | Recorded 804/808 checkpoint materialized successfully; fidelity gates pass at 40/40 |
| P8 | TTN / graph-TN / TNO | Exact TTN control passes; target D2/D4/D8 and TTN-derived BP are unstable; graph-BP/TNO rejected; no promoted candidate |

P5 and P9 are validated known-answer controls, and P8 has a recorded
tail-materialization result that passes the calibrated 40/40 fidelity gate. P6
has no verified answer: its completed loose-cutoff runs are flat. The new target
TTN implementation was validated on a small exact control but rejected on P8
for bond-level instability; routine parameter retries are not justified by the
current evidence.
