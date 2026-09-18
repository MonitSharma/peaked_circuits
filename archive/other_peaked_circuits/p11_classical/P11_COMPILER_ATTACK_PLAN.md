# P11 compiler attack plan

This branch tests compiler-level deobfuscation independently of the closed
MPO, MPS, static/dynamic permutation, graph, DTW, and sparse-state branches.
The campaign is P9-supervised and P11-blind.

## Ordered paths

1. Exact QASM normalization: one-qubit fusion, identity elimination, exact
   inverse cancellation, commuting diagonal gates, and virtual permutation
   bookkeeping.
2. Exact 2–4-qubit local block synthesis with direct unitary verification and
   explicit local output-permutation enumeration.
3. Three bounded partition offsets and center-out peeling on P9.
4. Controlled approximate replacement only at tolerances `1e-8`, `1e-6`, and
   `1e-4`, with a conservative error ledger.
5. Freeze only a verified, materially reducing P9 protocol; then apply it
   blindly to P11.
6. Use bounded DD or reduced-circuit simulation only after the relevant gates
   pass.

Every branch records before/after gate counts, circuit hashes, verification
status, resource limits, and a branch verdict. Historical result directories
are preserved.
