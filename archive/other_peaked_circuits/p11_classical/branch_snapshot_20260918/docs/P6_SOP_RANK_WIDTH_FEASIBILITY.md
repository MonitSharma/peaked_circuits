# Quadratic SOP / rank-width for P5/P6/P8/P9 — closed by the controls

**Verdict: closed.** Every circuit's cut-rank equals its qubit count exactly,
including the three already solved. The parameter has no discriminating power in
this family.

## Why it was worth trying

The gate-set match is exact, not approximate:

```
U3(t,p,l) = Rz(p) . Ry(t) . Rz(l)      Ry(t) = S . H . Rz(t) . H . S^dag
=>  U3 = [diag] H [diag] H [diag]
```

so P5/P6/P9 rewrite exactly into `{H, arbitrary diagonal 1Q, CZ}` with two H per
U3 and no angle snapping. P8's iSWAP is `SWAP . CZ . (S x S)`, where SWAP is a
wire relabelling. The 2026 result gives cost `poly(|C|) . 4^rw(G_C)` for that gate
set, with `rw` the rank-width of a Boolean path-variable graph -- a parameter
*different* from the tensor-network contraction width that already defeated the
cotengra rehearsal (W=119). Arbitrary diagonal 1Q gates contribute only **unary**
phase weights and add no edges, which is precisely the structural advantage
CAMPS lacked, where those same rotations became 14,308 non-Clifford residuals.

## Construction

`scripts/sop_rank_width.py`. Variables are wire segments between H gates
(`|vars| = #H + n`). Edges come from the H terms `x_prev . x_next` along a wire
and from the quadratic phase of each CZ/rzz across wires. Diagonal 1Q gates add
none.

Cut-rank of a bipartition is the GF(2) rank of the A x B adjacency submatrix;
the maximum along a linear order upper-bounds linear rank-width, and
`rank-width <= linear rank-width`.

**Validated before use**: vertex and edge counts match the rewrite exactly
(`vars = n + 2*n_u3`, `edges = 2*n_u3 + n_cz`) on three random circuits, and the
incremental GF(2) cut-rank agrees with a brute-force numpy rank at three cut
positions each. All checks pass.

## Result

Sweeping cut positions in circuit-time order, 24 cuts per circuit:

| circuit | qubits | path vars | edges | H gates | **max cut-rank** | cost | solved? |
|---|---:|---:|---:|---:|---:|---|:--:|
| P5 | 44 | 7,700 | 9,548 | 7,656 | **44** | 4^44 = 2^88 | **yes** |
| P8 | 40 | 3,672 | 4,520 | 3,632 | **40** | 4^40 = 2^80 | **yes** |
| P9 | 56 | 7,836 | 9,697 | 7,780 | **56** | 4^56 = 2^112 | **yes** |
| P6 | 62 | 14,046 | 17,478 | 13,984 | **62** | 4^62 = 2^124 | no |

**Cut-rank equals qubit count in every case.** A time-ordered sweep cuts all `n`
wires simultaneously, and no ordering along circuit time improves on the circuit's
own width.

## Why the control is decisive

P5 and P9 are solved circuits and this method reports 4^44 and 4^56 for them. A
parameter that declares already-solved problems infeasible cannot be used to
argue anything about P6. Identical to the CAMPS outcome.

## Caveat

This measures linear rank-width along **circuit-time order**. True rank-width can
be strictly smaller under a tree decomposition, and a better vertex ordering
could lower the linear bound. So 62 is an upper bound from one ordering, not a
proof.

The counter-argument is the control again: a decomposition clever enough to
rescue P6 would presumably also help P5 and P9, which are already solved by other
means. Residual chance estimated in the low single digits, against a substantial
implementation.

## Artifacts

`scripts/sop_rank_width.py`, `results/sop_rank_width/all_circuits.json`.
