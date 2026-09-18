# Sparse implementation audit

Initial audit of the published repositories at the recorded commits:

| implementation | source | commit | license | published behavior |
|---|---|---|---|---|
| qstvec | `external/qstvec` | `545614fa196e2a77d96d408e0cdf39520684b251` | MIT | sparse basis dictionary-like arrays, exact gate evolution followed by top-k or p-mass truncation |
| BASS | `external/bass` | `e591cf97316026da0cb681f787406361d1e5106e` | MIT | uint64 sparse keys, fixed-basis top-k baseline, adaptive local-basis RDM optimization, deferred truncation and PR do-no-harm guard |

## qstvec

`qstvec.Statevector` stores sorted/merged basis indices in `np.int64` and
complex128 amplitudes. `evolve` applies a supplied dense local matrix and
merges duplicate basis states. `truncate(top_k, p_frac)` retains largest
probabilities and renormalizes. `bit_string` returns the largest stored
probability. The implementation supports at most one signed 64-bit basis word
in practice, so P9 is directly supported and P11 is not. The GPU package is a
separate CuPy implementation and is not part of this CPU campaign.

Important convention: qstvec's local index is little-endian over `qargs`
(first qarg is local least-significant bit). The adapter converts Qiskit
operator matrices into that convention.

## BASS fixed

`FixedBasisSimulator` uses `SparseState` with `np.uint64` keys and complex128
amplitudes, a Numba open-addressing hash table for 2q gates, top-k or random-k
truncation, and cumulative `gamma` tracking. Its all-ones uint64 empty sentinel
is valid only while N is below the 64-bit boundary; the code documents roughly
N <= 63. It reports support, gamma history, and runtime but does not provide a
computational-basis reconstruction problem because its frame is fixed.

## BASS adaptive

`BASS` maintains local 2x2 basis transforms `U[j]`, conjugates gates into the
current frame, uses the same sparse core and hash table, and periodically
optimizes single-qubit RDM eigenbases. Rotations are accepted only when PR
strictly decreases; optional 2q rotations are separate. It uses deferred
truncation, a hard buffer cap, and `gamma` tracking. `to_statevector` folds the
local transforms back for N <= 24 only; there is no scalable computational-Z
top-k endpoint for large N. This endpoint limitation must be tested on P9
before any P11 consideration.

## Separation of layers

- **Published behavior:** the source behavior summarized above.
- **Repository implementation:** the unmodified snapshots under `external/`.
- **Our adapter logic:** exact Qiskit QASM parsing, matrix/order conversion,
  common metrics, provenance, and validation harnesses.
- **Future modifications:** any 128-bit key layer or BASS Z-basis decoder,
  allowed only after the corresponding P9 GO gate and recorded as explicit
  patches/commits.

Convenience classes such as BASS `RXGate` and `RZZGate` are not used as the
initial source of truth because their signs/parameterizations need not match
OpenQASM/Qiskit. Exact instruction matrices are the canonical input.
