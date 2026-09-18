# P8 suggestion implementation ledger

This document records what was implemented from the proposed P8 plan, what was
actually run, and what the resulting evidence means.

## 1. Expose the iSWAP permutation structure

Suggested change:

```text
iSWAP(a,b) = SWAP(a,b) · CZ(a,b) · (S(a) ⊗ S(b))
```

Implementation:

- `src/p12_recovery/peak/iswap_frame.py`
- `scripts/lower_p8_iswap_frame.py`
- `tests/test_iswap_frame.py`
- `results/p8_iswap_frame/p8_permutation_frame.qasm`

The frame circuit contains 1816 `u3`, 1776 `s`, and 888 `cz` operations, with
no explicit `iSWAP` or `SWAP` gates. Five exact local tests passed, including
state and permutation bookkeeping checks.

Result:

- Matched HPC line-MPO smoke test: `4/808` work gates.
- Direct native-iSWAP control: `101/808` in the same bounded test.

Conclusion: the identity is correct, but exposing the permutation made the
existing one-dimensional line-MPO solver worse. This falsified the specific
combination “permutation frame plus current line-MPO unswap solver”; it did not
falsify a geometry-preserving graph contraction.

## 2. Stop before the terminal routing attractor

Suggested change:

> Do not force the bulk router from roughly 784/808 toward 804/808. Hand off
> the live MPO and residual circuit before the attractor.

Implementation:

- `hpc/solver_patches/0002-p8-terminal-handoff.patch`
- CLI option: `--terminal-handoff-gates N`
- Bundle option: `--save-mpo`

The handoff stops compression when `N` or fewer work gates remain and preserves
the live MPO, residual left/right layers, virtual frames, and factor metadata.
The patch was applied only to an isolated HPC solver copy; the user's active
HPC checkout was not overwritten.

The first threshold tested was 12. It was too late: a clean run stalled around
784/808 and never entered the 12-gate window.

The threshold was then changed to 32, as suggested. A native-iSWAP P8 run
successfully stopped at exactly:

```text
776/808 consumed
32 work gates remaining
core MPO maximum bond = 106
```

This produced the first genuine P8 handoff bundle.

## 3. Global tail contraction

Implementation:

- `scripts/solve_p8_tail_bundle.py`
- `scripts/report_p8_tail_state.py`

The consumer loads `mpo_dump.pkl`, removes measurement instructions from the
unitary tail, constructs the left inverse and right residual operators, and
contracts them with the saved core MPO. It also supports saving the final MPS,
sampling/top-k output, and rejecting malformed factor mappings.

The first one-shot implementation consolidated the entire residual side into a
single MPO. It ran for more than an hour without producing output and was
stopped. This demonstrated that the one-shot operator construction was too
expensive in the current representation.

The implementation was changed to staged tail contraction. Each tail is split
into chunks, with compression after every chunk. The chunk limit was then
corrected to count all unitary operations, including routing SWAPs, rather than
only logical work gates.

## 4. Tail bond ladder on the same frozen P8 bundle

All runs below used the same 776/808 handoff bundle, so the expensive bulk
trajectory was not rerun.

| Tail bond limit | Result | Final norm | Bond cap reached | Runtime |
|---:|---|---:|:---:|---:|
| 256 | completed | 0.8022889821 | yes | not retained in summary |
| 512 | completed | 0.8058445000 | yes | 302.6 s |
| 1024 | completed | 0.8063847193 | yes | 1082.2 s |

The D=256 run initially failed only during sampling because Quimb encountered
a canonicalization tensor-shape error. The state itself had already been
saved. The standalone state reporter recovered its bond and norm metrics.

The D=512 run completed and saved a roughly 206 MB state. The D=1024 run
completed and saved a roughly 718 MB state. Neither produced a converged state:
the maximum bond was saturated at every tested bond limit, and the norm
improvement from 512 to 1024 was only about 0.00054.

## 5. Resulting committed files and commits

Relevant committed artifacts:

- `250dbea` — exact iSWAP permutation frame
- `a80ff11` — frame smoke comparison evidence
- `f409f25` — explicit terminal handoff patch
- `6e81873` — initial global tail consumer
- `b2207c7` — method-status report
- `0ab30c6` — tail state decoding and mapping checks
- `983baff` — measurement-layer handling fix
- `ec8e287` — staged tail contraction
- `59bf593` — chunking corrected to count SWAPs
- `4e0f7cd` — D=512 result
- `d3be5c1` — standalone saved-state reporter
- `c0fbe2f` — D=1024 result

Current branch is `p11_classical`, synchronized with GitHub.

## 6. HPC-only artifacts

The large tensor artifacts remain on HPC and were intentionally not committed
to GitHub:

```text
/home/hclau/p12-helios-recovery/results/p8_terminal_handoff/capture32/p8_capture32/mpo_dump.pkl
/home/hclau/p12-helios-recovery/results/p8_terminal_handoff/capture32/p8_tail_D256_staged_state.pkl
/home/hclau/p12-helios-recovery/results/p8_terminal_handoff/capture32/p8_tail_D512_staged2_state.pkl
/home/hclau/p12-helios-recovery/results/p8_terminal_handoff/capture32/p8_tail_D1024_staged_state.pkl
```

The compact JSON summaries for D=512 and D=1024 are committed under:

```text
results/p8_terminal_handoff/capture32/
```

## 7. Current conclusion

The proposed workflow was implemented and reached its intended handoff point.
The bulk router no longer needs to reach 808, but the 32-gate residual tail is
too entangled for the current line-MPO contraction: D=256, 512, and 1024 all
saturate their caps without norm convergence.

Therefore the evidence now supports closing this particular terminal-MPO path
unless D=2048 is needed as a final upper-bound diagnostic. The next serious
method should be a genuinely geometry-preserving native-grid contraction, not
another attempt to tune the same line-MPO router.

## 8. MAP-decoder follow-up

The requested D=256/D=512/D=1024 MAP comparison was attempted before any
D=2048 run. The saved states are Quimb MPS objects with one residual nonlocal
virtual bond crossing sites 20--22, so the standard chain extractor could not
consume them directly. A decoder-side exact conversion was added to carry that
bond through the intervening sites as an enlarged chain bond.

The repository `best_first_map` search then became the limiting step: the
unbounded three-state decode and a bounded 10,000-node D=256 decode both exited
without a result artifact. No certified MAP, runner-up, or Hamming distance can
therefore be claimed from this attempt. The states themselves remain valid and
their D=256/512/1024 norm and bond results are unchanged. This is a decoder
tractability failure, not evidence of candidate disagreement.
