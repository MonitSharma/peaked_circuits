# P6 GPU feasibility screen

This is a CPU-only screen. It makes no provider calls, starts no jobs, and does
not claim a tensor-level contraction result. It records what can be established
locally before paying for a GPU.

The exact frozen QASM has 62 qubits, 6,992 `u3` gates, 3,494 `cz` gates, and a
connected 62-node interaction graph. A dense complex128 statevector would need
64 EiB before simulator overhead.

The local environment contains NetworkX, but no `cotengra`, `opt_einsum`,
`cuquantum`, Qiskit Aer, or CUDA runtime. Therefore we can compute only logical
graph heuristics locally; a real tensor-network contraction path estimate still
needs a path optimizer or a remote environment.

The previous P6 CPU MPS/MPO campaign already tested the practical approximate
state-evolution route. It found the usual completion/fidelity tradeoff: tight
settings stalled and loose settings completed without a validated peak.

## Tensor-level estimate

After installing the lightweight `opt_einsum` path optimizer, we constructed an
exact amplitude network from the frozen QASM: initial state tensors, every `u3`
and `cz` gate, and final computational-basis projections. A CPU greedy path
search completed in about 10 seconds. Its largest intermediate was `2^424`
elements, or approximately `6.0e110 EiB` in complex128 storage. This is a
heuristic upper bound, not an optimality proof, but it rules out a straightforward
single-GPU contraction and makes ordinary cloud GPU rental unjustified.

The estimate is saved in `tensor_path_estimate.json`. The path search did not
contract the numerical tensors and made no provider calls.

## Decision

Do not rent GPU time for a direct full-network contraction. The next serious
option would require a different representation: slicing, a low-rank
approximation, circuit cutting, or exploiting a problem-specific algebraic
structure. Those methods need a concrete accuracy target and validation plan;
they are research projects rather than a routine GPU rerun.

Machine-readable results are in `feasibility.json`.
