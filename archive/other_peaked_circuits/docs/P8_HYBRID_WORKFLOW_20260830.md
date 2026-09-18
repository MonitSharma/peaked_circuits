# P8 hybrid classical/IBM workflow

Status: local prototype complete; no IBM job submitted in this phase.

## Classical stage

The exact P8 QASM was run with the existing bounded TTN runner, answer-blind,
using the immutable input hash recorded in `configs/peak_recovery/P8.json`.

| run | status | result |
|---|---|---|
| TTN, max bond 8, cutoff 1e-10 | complete, 200.0 s, 0.91 GiB peak RSS | `0101010001111100110101000111001001001000` |
| TTN, max bond 16, cutoff 1e-10 | safely aborted at 300 s | 500/2,704 gates; about 10.6 GiB RSS; no candidate |

The D=8 candidate is therefore a provisional member of the candidate pool,
not a promoted answer. The D=16 result shows that simply increasing the bond
dimension is not currently an efficient path on this Mac.

Post-freeze evaluation subsequently reported an overlap of **19/40** for the
D=8 candidate. This is held-out validation only; it was not used to alter the
candidate pool or tune the simulation. It confirms that the bounded D=8 TTN
candidate is not reliable enough to justify hardware verification.

## Frozen candidate and observable prototype

Seven candidates were frozen before any new hardware data was consulted. The
local prototype computes empirical `Z_i` and `Z_i Z_j` statistics from the
pre-existing 1,000-shot classical MettleQ sample file. This is a software
prototype for the future IBM observable interface, not a hardware result.

The ten least-polarized bits in that classical sample are positions:

`12, 34, 11, 25, 18, 17, 32, 22, 6, 28`

The top-20 pair correlations and all candidate scores are preserved in
`results/p8_hybrid_20260830/local_observable_proxy.json`. The candidate pool
hash is recorded there, and `external_target_scored` remains false.

The local proxy ranked the original MettleQ candidate first. This is not
independent evidence: it is expected because the same classical samples define
the proxy. IBM measurements must therefore be evaluated on held-out or
independent calibration cases before use.

## Operator backpropagation and circuit cutting

The IBM add-ons were installed in the authenticated Qiskit environment and
small three-qubit control tests passed for both operator backpropagation and
wire cutting. A strict 10-second P8 backpropagation probe did not finish within
the operator budget; the package's timeout path returned an internal
`UnboundLocalError`. This is a software/prototype blocker, not evidence that
P8 itself is unsuitable.

No hardware workload was submitted under these methods. Before using them on
IBM, the implementation must:

1. verify exact QASM semantics and bit ordering;
2. set a maximum Pauli-term/operator budget for backpropagation;
3. set a maximum number of cuts and a reconstruction-sampling budget;
4. abort when those limits are exceeded;
5. validate reconstructed observables on small circuits and known-answer
   controls.

## IBM submission gate

No reduced IBM workload is justified yet. A submission becomes appropriate only
after a concrete reduced circuit or observable workload exists, its local
reconstruction agrees with direct simulation on controls, and the estimated
cost is materially below full P8 execution. The prior IBM full-circuit P8 runs
were diffuse, so another full-circuit shot campaign is not the next step.

The separate quantum-advantage claim remains out of scope for this recurrence
and candidate-ranking workflow.
