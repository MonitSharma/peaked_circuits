# Classical Simulations of P11 and P12

Reproduction and performance extensions by Monit Sharma, built on the original
classical structural-reduction solver from **Dylan Neve / qsim-lab**. The tracker
submission credits **Dylan Neve and Claude (Anthropic)**. The original method
and discovery belong to that work, not to this repository.

## Original Work and Attribution

- Original repository: [dylanneve1/qsim-lab](https://github.com/dylanneve1/qsim-lab).
- Original solver: [solve_peaked.py at commit 03e5774](https://github.com/dylanneve1/qsim-lab/blob/03e5774655b33937d01117f07575a00ec14805e5/research/data/peaked-circuits/solve_peaked.py).
- Original explanation: [Cracking the 98-qubit peaked circuits P11 and P12 classically](https://github.com/dylanneve1/qsim-lab/blob/03e5774655b33937d01117f07575a00ec14805e5/research/simulability/peaked-circuits.md).
- Original submission and discussion: [Quantum Advantage Tracker issue #251](https://github.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io/issues/251).

The upstream method fingerprints inter-CZ single-qubit rotations modulo global
phase, identifies unique inverse anchors, and infers nested identity blocks and
wire involutions. It replaces most of the middle with a wire permutation,
contracts the shallow reduced core with quimb/cotengra, and greedily repairs
boundary gates by maximizing the reduced-core candidate probability.

`qsimlab_original.py` preserves the downloaded original. The new solver imports
its circuit parser, gate matrices, fingerprinting, and section detector.
Its Git blob SHA is `6658146b0021abb57a555688572e2741b301b822`.
The upstream MIT copyright and permission notice are retained in [LICENSE](LICENSE).
Code added in this folder is also distributed under that MIT license; the
repository's existing Apache-2.0 license remains unchanged outside this folder.

## Changes in This Reproduction

Implemented improvements:

- Stable candidate order and selection of the best candidate satisfying the
  improvement threshold relative to the current core, rather than the current
  best trial.
- Exact marginal reuse when the ordered backward causal cone is unchanged.
- Greedy contraction-path caching with tensor-order, connectivity, output, and
  dimension checks; no approximate contractions are introduced.
- Reuse of the accepted trial instead of recalculating it.
- Numerical certification of the reduced core's unique global mode using
  marginal bounds and explicit competing amplitudes.
- Conflicting, non-bijective, and ambiguous anchor maps are rejected. Reciprocal
  involution constraints complete the P11/P12 maps without factorial search.

This is still the P11/P12 structural-reduction method. General QASM parsing,
beam-search repair, and MPO fallback are not implemented in this version.
Neither this solver nor its certificate proves equivalence between the reduced
core and the full published circuit. Output probabilities and certificates
apply only to the reduced core, to the stated numerical tolerance.

## Run

Tested with Python 3.13.2 and the packages in `requirements.lock.txt`.

```sh
cd classical_simulations/p11_p12
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python -m unittest -v test_solver.py
.venv/bin/python solve_peaked_improved.py P11.qasm P12.qasm \
  --verify-cache --output-dir results
```

The included QASM files are the canonical [Quantum Advantage Tracker circuits](https://github.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io/tree/1db844f1540a198c5620af49247e09fc28e7f61b/data/classically-verifiable-problems/circuit-models/peaked_circuit)
at commit `1db844f1540a198c5620af49247e09fc28e7f61b`:

- P11 SHA-256: `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`
- P12 SHA-256: `868ff86a396f86a8cbca48f7127e49c4c4f951a5a955295e5010a92b76be961d`

`--verify-cache` independently recomputes every final marginal and checks it
against the cached results. Solver time excludes this extra validation and the
separately timed certification, imports, and dependency installation.

To measure the same deterministic search with caching disabled:

```sh
.venv/bin/python solve_peaked_improved.py P11.qasm P12.qasm \
  --no-marginal-cache --no-path-cache --output-dir uncached-results
```

No expected peak is used at runtime by either solver. Reference comparison is
performed after the solve. This is a reproduction on already-public instances,
not a fresh holdout experiment. The upstream writeup explicitly discloses that
boundary repair was developed after an initial P12 result differed from the
hardware peak by four bits.

## Verified Local Results

Both instances match all 98 published target bits. Six focused tests passed.
Every final cached marginal matched an independent fresh contraction exactly
in these runs. The uncached run used `PYTHONHASHSEED=27` and reproduced the same
repair paths and probabilities as the cached run.

| Instance | Same search without caches | Cached solve | Speedup | Certification | Core probability |
| --- | ---: | ---: | ---: | ---: | ---: |
| P11 | 50.285 s | 17.089 s | 2.94x | 0.057 s | 0.302893357 |
| P12 | 86.340 s | 27.941 s | 3.09x | 1.773 s | 0.236559451 |

Solving plus certification took 17.146 s and 29.714 s respectively. Extra
cache-validation contractions took 2.669 s and 2.538 s respectively; including
those checks, total times were 19.815 s and 32.253 s. These are single-run local
measurements, not hardware-independent runtime guarantees.

P11 selected R-boundary gate 59. P12 selected R-boundary gates 60 and 64.
Marginal reuse was 78.125% and 82.8125% respectively.

Both candidates are numerically certified unique global modes of their reduced
cores. P11 has probability 0.302893357, while all competitors are bounded at
most 0.281216378. P12 has probability 0.236559451, while all competitors are
bounded at most 0.218386619. Certification used one competing amplitude for
P11 and 31 for P12. The proof bounds strings differing on any excluded wire
by that wire's opposite-bit marginal, and enumerates all strings differing
only on the remaining ambiguous wires.

Detailed records are in `results/`, `uncached-results/`, `improved-run.log`, and
`uncached-run.log`. Recorded absolute input paths were normalized to `P11.qasm`
and `P12.qasm` for publication; numerical values and timings are unchanged.
To independently compare the completed results with the
published targets and regenerate `benchmark-summary.json`, run:

```sh
.venv/bin/python verify_results.py
```

`verify_results.py` contains the public reference strings for this post-solve
comparison. The solving and certification modules do not import or read them.
