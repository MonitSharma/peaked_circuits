# P8 complete method history and current status

> **RESOLVED 2026-09-01: P8 IS SOLVED.** The answer was obtained by
> materializing the MPS at the 804/808 routing stall, which folds the 4
> remaining work gates into the residual layers. The "P8 remains unresolved"
> assessments below are historical. See `docs/P8_TAIL804_CANDIDATE.md`.

## Executive summary

P8 is a 40-qubit, depth-129 circuit with 1,816 U3 gates and 888 native iSWAP
gates, consolidated by the production workflow to 808 work gates. Its native
interaction graph has 63 edges and maximum degree 4. The target is the dominant
computational-basis output, but no target bitstring has been certified.

The strongest historical production result is 804/808 work gates. That run did
not reach sampling. **Its provenance is now resolved: the 804 trajectory was
reproduced exactly on 2026-08-31 at solver commit `7296a2a`, with all six
recorded state fields matching bit-for-bit** (804 gates, `no_progress_cycle_limit`,
final bond 105, final elems 215604, peak bond 272, peak elems 688728, leftover
L=2/R=17). The earlier "dirty checkout" was simply the uncommitted `--flip-freq`
exposure, later committed as `7296a2a`; `e1a6eef` hard-codes `flip_freq=None`.
See `docs/P8_804_FORENSIC_RECONSTRUCTION.md` §Resolution. Clean
tail-materialization attempts stopped at 781/808 and 782/808, but those started
from checkpoints produced without the flip-freq path and should be re-run from
the reproducible 804 checkpoint.
All approximate candidate-producing alternatives tested so far failed their
fidelity, stability, positivity, or convergence gates.

The latest native-graph experiment is scientifically useful but not yet a
solution: direct native-iSWAP evolution with Quimb 2-norm BP compression is
finite at chi 16/32 on a 100-event prefix, while chi 4/8 lose substantial norm
and higher-chi BP becomes expensive. A correlation-aware projection beam
decoder is implemented and passes small correlated controls, but full P8
projection/regauging is currently too slow under the bounded pilot.

## 1. Starting point: line-MPO routing

The original production route represented P8 as a line MPO and used midpoint
compression, greedy unswapping, SABRE routing, and absorption heuristics. The
historical nineteen-run campaign covered routing scores, seeds, patience,
center ratios, selectors, and bond settings. It consistently stalled between
779 and 799 of 808 gates.

The telemetry identified a routing attractor rather than a simple bond-cap
failure:

- selected absorptions hit the maximum bond zero times;
- increasing D from 512 to 1024 did not solve the stall;
- legal absorption choices remained available;
- routing SWAP layers were inserted, absorbed no work gates, and then removed;
- 94 routing-state hashes contained only 32 unique states;
- the best baseline endpoint had the left half complete and the right half
  stranded at approximately 395/404.

Changing SWAP selection did not escape the attractor. Absorption scheduling did
have leverage: `flip_freq=1` reached 802/808 and `flip_freq=2` reached 804/808,
versus 799/808 for the baseline. However, none reached the final sampling
stage. Thus this route was not disproved as a matter of arithmetic, but the
bulk controller was not a reliable path to a candidate.

Relevant evidence is in `docs/P8_MPO_DIAGNOSIS.md`.

## 2. iSWAP permutation-frame method

The proposed identity was implemented exactly:

```text
iSWAP(a,b) = SWAP(a,b) · CZ(a,b) · (S(a) ⊗ S(b))
```

The SWAP was represented as a logical/physical permutation, not as a tensor.
The implementation produced a frame circuit with 1,816 U3, 1,776 S, and 888
CZ operations and no explicit SWAP or iSWAP gates. Five local exactness and
mapping tests passed.

What failed was the combination of this representation with the existing
one-dimensional line-MPO unswap solver. Under matched bounded settings it
reached only 4/808, while the direct native-iSWAP control reached 101/808.
The identity itself is correct; the line-MPO ordering still paid for dynamic
permutations and became worse. This did not test a genuine geometry-preserving
contraction.

Files: `src/p12_recovery/peak/iswap_frame.py`,
`scripts/lower_p8_iswap_frame.py`, and `results/p8_iswap_frame/`.

## 3. Terminal handoff and tail contraction

The next proposal was to stop the bulk router before the attractor, save the
live MPO and mappings, and contract the residual tail separately. A threshold
of 12 gates was too late: the bulk run stalled around 784/808. A threshold of
32 succeeded in producing a genuine handoff at 776/808, with 32 work gates
remaining and core maximum bond 106.

The first one-shot tail contraction was stopped after more than an hour with
no output. It was replaced by staged tail contraction with compression after
each chunk. Chunk accounting was corrected to include all unitary operations,
including routing SWAPs. Mapping serialization was later hardened so candidate
output fails closed when factor-to-logical mapping metadata is absent.

On the same frozen 776/808 bundle:

| tail bond | outcome | final norm |
|---:|---|---:|
| 256 | completed | 0.8022889821 |
| 512 | completed | 0.8058445000 |
| 1024 | completed | 0.8063847193 |

All three saturated their bond limits. D512 and D1024 improved the norm only
slightly, and the saved states were not norm-converged. The requested MAP
decoding of these states also failed to produce artifacts: a residual nonlocal
bond complicated chain extraction and the best-first decoder became the
limiting step. Therefore no stable MAP comparison or candidate was obtained.

The large pickle states remain HPC-only; compact summaries are committed under
`results/p8_terminal_handoff/capture32/`.

## 4. Structural and alternative tensor-network routes

Several alternatives were tested or bounded:

- Identity, spectral, and permutation MPS orders produced extremely small
  retained-norm proxies; the P8 D256 annealed permutation-MPS run retained
  `7.3925e-19`, below the required `100*2^-40 = 9.095e-11` gate. Its top-1 /
  top-2 ratio was only 1.020 and its top-32 spread was 7.9 bits. It was
  rejected as a truncation artifact.
- Weighted TTN topologies covered all 40 qubits and passed small exact
  controls, but P8 D2/D4/D8 candidates differed by 15, 24, and 17 bits, with
  large discarded-weight proxies. The family was rejected as unstable.
- Pairwise graph-BP passed a tree-factorized control, but target P8 factors
  failed positivity checks. A Frechet-bounded projection made a diagnostic
  run possible, but changed factors substantially and was not promoted.
- Mirrored-TNO feasibility was blocked by a missing optional `tnag` module in
  one environment and timed out in another. No candidate was produced.
- Local-unitary and graph/mirror scans found strong short-window matches, but
  graph permutation stability was only 0.0167 and controls with mismatched
  windows were significant. No global mirror/permutation was established.

These results ruled out treating a large ratio or a visually structured local
signal as sufficient evidence. Fidelity, norm retention, cross-method
stability, and mapping correctness remained mandatory.

## 5. Exact native-amplitude contraction rehearsal

Cotengra was asked only to optimize a contraction tree for one fixed native P8
amplitude. No contraction was executed. The rehearsal estimated width 56,
approximately `1.967e23` FLOPs, and a largest intermediate of `2^56`
complex128 elements (about 1 exabyte). Slicing to 4, 16, 32, or 64 GB still
left astronomical slice counts. Exact fixed-amplitude adjudication was
therefore closed as infeasible in the current representation.

Artifact: `results/p8_native_amplitude_rehearsal.json`.

## 6. Sparse computational-basis statevector

Because iSWAP only permutes basis indices and applies phases, it preserves the
number of active sparse basis states. The sparse simulator therefore focused
support growth on the 1,816 U3 gates. Exact small Qiskit controls passed with
maximum error about `1.76e-16`.

The bounded top-k ladder was a falsification experiment, not an assumed
solution. Candidates were unstable: at the tested k values, successive
solutions changed by 21 and 14 bits and top-1/top-2 separation was weak. The
`2^20` run already took about 691 seconds, so larger k values were stopped.
The p-mass settings with hard caps did not establish a stable candidate.

Artifacts: `scripts/run_p8_sparse.py`,
`scripts/validate_p8_sparse_qiskit.py`, and
`results/p8_sparse_bounded_ladder_summary.json`.

## 7. Native interaction graph and BP environment method

The original native circuit was reconstructed as a 40-node, 63-edge graph.
Every native iSWAP was verified to lie on an actual graph edge. The graph is
planar and grid-like, but is not an exact subgraph of a standard 5x8 grid; its
degree sequence differs from that grid.

The new solver keeps virtual bonds only on native graph edges, applies iSWAP
directly to adjacent graph tensors, and performs Quimb 2-norm BP compression
after the exact local post-gate split. U3 gates do not trigger a BP solve,
since they cannot change virtual bond structure. Product-state rank-one bonds
are skipped because there is no nonzero environment for BP to condition.

On the first 100 P8 events:

| chi | final norm | observed max bond |
|---:|---:|---:|
| 4 | 0.5664754208 | 4 |
| 8 | 0.9705696303 | 8 |
| 16 | 1.0000000000 | 16 |
| 32 | 1.0000000000 | 16 |

The chi=4 300-event prefix completed in 66.5 seconds but fell to norm
0.0377589228. Higher-chi 300-event runs became too slow for the bounded pilot.
This demonstrates that BP compression is operational and that higher chi helps
retention, but it does not demonstrate full-circuit convergence. No chi=64
run was justified.

Artifacts: `src/p12_recovery/peak/native_graph_state.py`,
`scripts/run_p8_native_graph_bp.py`, and
`results/p8_native_graph_bp/`.

## 8. Correlation-aware sequential decoder

The graph state must not be decoded from one-site majority marginals. The new
decoder instead branches on each bit, projects the selected physical tensor,
canonically regauges the child network, scores it by projected norm, and keeps
the top B branches. It supports B=16, 32, and 64 and emits original logical
qubit order.

A two-qubit correlated control recovered the exact support structure at beam
widths 1, 2, and 4. A P8 100-event chi=16 decode with B=16/32/64 was started
on HPC, but full-network copying and regauging exceeded the bounded runtime.
This is a performance limitation of the current decoder implementation, not a
candidate disagreement. No P8 bitstring is certified by it.

Artifact: `src/p12_recovery/peak/native_graph_decoder.py` and
`docs/P8_GRAPH_BEAM_DECODER.md`.

## 9. Current scientific status and next justified work

**P8 is solved as of 2026-09-01** (see the header). The conclusions below were
written before that and remain accurate as descriptions of the individual
method failures -- with one correction: item 1's "not proven entanglement
saturation" was right, but the campaign wrongly inferred that failing to consume
all 808 work gates meant no candidate was obtainable. Materializing at the 804
stall with 4 gates remaining produced the correct answer.

Historical assessment follows.

P8 was then unresolved. The evidence supported these conclusions:

1. The old line-MPO problem is primarily a routing/order attractor, not proven
   entanglement saturation.
2. The iSWAP permutation identity is exact, but it does not rescue a line-MPO
   representation.
3. Tail-MPO contraction reaches a useful handoff but is not norm-converged and
   has not yielded a certified MAP.
4. Sparse statevector, MPS, TTN, graph-BP, and exact-amplitude routes have
   failed their respective stability, fidelity, positivity, or resource gates.
5. Native graph evolution with a 2-norm BP environment is the most principled
   remaining route, but it needs localized environment updates and efficient
   branch projection before a full P8 decode is practical.

The immediate engineering priority is therefore to avoid deep-copying and
regauging the entire graph for every beam branch. Until that is optimized and
validated on larger exact controls, no full P8 candidate should be submitted,
and no chi=64 run should be launched.

## Reproducibility and provenance

All recent work was performed on branch `p11_classical`. Safe Quimb pilots ran
in the isolated HPC environment `.venv-mpo-py310`; the fragile `p9-openblas`
environment was not modified. Large tensor states were intentionally kept off
GitHub. The compact code, summaries, tests, and this report are tracked in the
repository.
