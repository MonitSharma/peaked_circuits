# P6 tensor path summary

The exact P6 amplitude network contains 21,220 tensor factors and 14,042 index
labels when the 62-qubit initial state and final projection factors are included.
The greedy `opt_einsum` path search took 9.5 seconds on the Mac CPU.

Its largest intermediate contains approximately `2^424` elements. In complex128
that is approximately `6.0e110 EiB`. The optimized FLOP count is also
astronomical. This is an upper bound from one heuristic path, so it does not
prove that no better contraction exists. It does show that renting a normal
single GPU and sending the unmodified full network to it is not a sound next
step.

The exact circuit has 6,992 `u3` gates and 3,494 `cz` gates on 62 qubits. The
source QASM and submitted QIR audit already match, so this estimate is based on
the circuit actually used for the hardware jobs.
