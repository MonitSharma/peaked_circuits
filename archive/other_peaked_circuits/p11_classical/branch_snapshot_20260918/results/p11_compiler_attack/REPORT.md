# P11 overnight compiler attack report

Date: 2026-08-21  |  Branch: `research/p11-compiler-attack`  |  Baseline: `66ab53b`

## Result

Exhaustive local no-go. No verified compiler or bounded local replacement met
the P9 Gate A requirement. The best verified P9 and P11 two-qubit reduction is
0.0, so no protocol was frozen and no blind P11 transfer was authorized.

## Evidence

- Path A exact normalization: P9 remained `5807` total / `1917` two-qubit
  gates; input and output hashes matched.
- Paths B/C: exact q=2 local synthesis and the virtual permutation ledger
  accepted zero replacements. q=3/q=4 optional BQSKit synthesis was
  unavailable; each branch is recorded as unavailable rather than treated as
  a success.
- Paths D/E: offsets `0,1,2` and middle-out ordering produced zero accepted
  replacements on both fixtures.
- Path F: direct dense local verification passed for supported q<=4 candidate
  blocks at phase-insensitive fidelity `1 - 1e-10`.
- Path G: tolerances `1e-8`, `1e-6`, and `1e-4` produced zero accepted
  reductions. The known P9 `56/56` peak condition is preserved.
- Paths H/I: DD, PyZX, BQSKit, QCEC, and MQT DDsim are unavailable locally;
  direct local verification is the recorded fallback. The P11 blind protocol
  remains unrun because P9 did not freeze a successful protocol.
- Full regression: `130 passed in 35.68s`.

Artifacts are under `results/p11_compiler_attack/`; authoritative state is
`results/p11_overnight/RUN_STATE.json`.
