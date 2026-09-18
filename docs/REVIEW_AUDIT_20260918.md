# Third-party review before tracker submission

Review date: 2026-09-18

## Quantum Advantage Tracker status

The current tracker repository contains the P11 and P12 circuit definitions as
active peaked-circuit instances:

- `peaked_circuit_P11_Hqap_98x1999` — 98 qubits, 1,999 gates;
- `peaked_circuit_P12_Hqap_98x2457` — 98 qubits, 2,457 gates.

The current `data/classically-verifiable-problems/submissions.json` index does
not contain a P11 or P12 submission entry. A repository-wide search of the
current tracker checkout also found no P11/P12 issue or submission record. The
circuits are present, but our new P11/P12 submission has not yet been added to
the tracker repository.

## Independent checks performed

- The packaged P11 source QASM SHA-256 matches the tracker’s P11 QASM:
  `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`.
- The packaged P12 source QASM SHA-256 matches the tracker’s P12 QASM:
  `868ff86a396f86a8cbca48f7127e49c4c4f951a5a955295e5010a92b76be961d`.
- P11 contains 50 active canonical shots after removing the exact duplicate
  framing record; the 51-record reconstruction is retained separately.
- P12 contains 200 reconstructed canonical shots after structural framing
  repair.
- Weighted observed medoid and cluster consensus recover the accepted P11
  answer.
- Most-frequent string, weighted observed medoid, and cluster consensus recover
  the accepted P12 answer.
- Package checksums and required-artifact verification pass.

## Corrections made

- Added the supplied BlueQubit leaderboard screenshot to the main README.
- Updated repository links from the deleted `p12_quantum` branch to
  `peaked_circuits` `main`.
- Corrected the stale P11 classical runtime in the tracker-facing records.
- Removed obsolete decoder wording from the tracker-facing P12 narrative.
- Added shot-count and proof-link invariants to the package verifier.
- Hardened GitHub Actions installation, permissions, caching, timeout, and
  manual-dispatch behavior.

## Evidence boundary

The BlueQubit screenshot shows Monit Sharma’s overall leaderboard result of
2570/2570 and is useful corroborating evidence of portal acceptance. It does
not, by itself, attribute individual score points to P11 and P12. The tracker
issue should therefore link the per-problem raw hardware packages and state the
external acceptance record precisely, without claiming that the screenshot is
an independent proof of every decoder step.

No quantum-advantage claim is made by the current package. The proposed tracker
submission should remain a classically verifiable recovery submission unless a
separate classical-baseline and resource comparison supports a stronger claim.
