# PPS implementation audit

## Adapter

`scripts/export_pp_gate_stream.py` exports Qiskit instructions to a canonical JSON stream. Native PauliPropagation mappings are used for Clifford gates and `rzz`; arbitrary Qiskit `u` gates are serialized as exact computational-basis matrices and loaded as `TransferMapGate`. The qubit rule is explicit: `q_julia = q_qiskit + 1`.

## Independent validation

The Qiskit dense panel covered H, RX, arbitrary U, RZZ, CNOT/RZ/X, CZ, nonadjacent U/RZZ, and a generic two-qubit unitary. Nine cases agreed with dense Qiskit values at errors from zero through `2.22e-16`, well below `1e-10`; a separate measurement-permutation assertion also passed. This validates matrix ordering, gate conventions, Heisenberg direction, qubit indexing, generic two-qubit fallback, and measurement ordering.

## Canonical structural audit

P9 has 56 qubits and 5,807 gates: 1,917 RZZ rotations and 3,890 U gates. P11 has 98 qubits and 9,995 gates: 1,999 CZ gates and 7,996 U gates. P11 was inspected only structurally; no target or candidate information was sought.

The canonical stream SHA-256 values are P9 `45e526abdd74991d02faa28cb996ce9ce229dbfee0b617ef67e108757b1e0216` and P11 `91065a00c3015d2e009d63c418db77abd6a7a20bcb62e20616cb37fbdc9d84a8`.

## HPC state

The checkout was already dirty and at `dec79c47112543c028e0af68bed47e57ff46409f` when the campaign began, while the fetched SSH branch reference was `36938f94f2c77b9dacd4b7f6062fcc9276b70121`. Existing modifications and virtual environments were preserved.

## Tests and threading

The Julia package test suite passed 8 tests (3 adapter primitives plus 5 gate/overlap checks), and the existing Python suite passed `146 passed in 61.15s` with `-m 'not hardware'`. A deterministic 200-gate P9 prefix at `1e-3` was run on one NUMA node at Julia thread counts 1, 4, 8, and 18. All produced expectation `0.07475665106734851` and 1,982 terms; internal propagation times were 2.028, 1.936, 1.916, and 2.046 seconds respectively. External maximum RSS was 464--480 MiB including process startup. The 8-thread configuration was marginally fastest for this bounded workload, but this does not change the P9 no-go decision.
