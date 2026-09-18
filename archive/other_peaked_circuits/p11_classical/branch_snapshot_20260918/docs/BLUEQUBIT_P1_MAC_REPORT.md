# BlueQubit P1 Mac screening report

**Status:** bounded Mac screening complete; no HPC or cloud job launched.

## Provenance and blindness

The branch is `bluequbit-p1-classical`, created from `p11_classical` at
`1151be3bbf952fc8a8edb642cdd95e290a4e25c1`. The local P1 input remains outside
version control at `/Users/monitsharma/Downloads/P1_little_dimple.qasm`.
SHA256: `0a02afffbdcf6755d5ed16b3a10cddd40cde4ee072d6072dbe7013e1c42f2ff8`;
size: 219,814 bytes. No answer string, oracle, or hidden verifier was read.

## 1. P1 versus P9

| metric | P1 | P9 control |
|---|---:|---:|
| qubits | 36 | 56 |
| parsed operations | 4,407 | 5,807 |
| one-qubit gates | 2,950 | 3,890 |
| two-qubit gates | 1,457 | 1,917 |
| circuit depth | 307 | 207 |
| two-qubit depth | 153 | 103 |
| unique interacting pairs | 564 | 1,069 |
| simple mean degree | 31.333 | 38.179 |
| weighted mean degree | 80.944 | 68.464 |

P1 is smaller but more temporally dense: its two-qubit gates are concentrated
over fewer qubits and more two-qubit layers. The previously quoted “80.9 degree”
is weighted interaction frequency, not simple graph degree; simple degree is
bounded by 35 on a 36-vertex graph.

## 2. Is 97–99% progress real?

Not established by the artifacts currently available on this branch. The only
valid in-branch P1 MPO run is `mpo_baseline_300`: 1,413 total work gates, 114
observed at 105 seconds, 1,299 remaining, and an external 120-second wall guard.
It produced two native complex64 SVD convergence failures. The exact diagnosis
is in `results/bluequbit_p1/routing/TERMINAL_DIAGNOSIS.json`. The earlier 97–99%
claim is therefore classified **unsubstantiated**, not reproduced.

## 3. What is failing?

For the bounded MPO run, the evidence supports a mixed numerical/throughput
limitation: native complex64 SVD convergence failures occurred, but no persisted
bond-ceiling or terminal permutation telemetry proves tensor capacity or cycling.
The run was stopped by the external wall guard before the solver’s own
no-progress guard. It is scientifically incorrect to label this run definitive
swap-thrashing evidence.

## 4. Is midpoint 0.5 optimal?

The cheap ratio scan ranks 0.50 highest by weighted pair cosine (0.4734), with
0.55 close (0.4695) and 0.45 behind (0.4660). The structural mirror tool’s best
graph scores were at q2 cuts 632/776 for window 64 and 680 for window 128, so
the evidence does not uniquely select 0.5. These are structural rankings, not
solver-success rankings.

## 5. Does ordering help?

The initial deterministic proxy scan does not show a useful improvement over the
original order. Original and reversed order have weighted edge span 17,011 and
maximum weighted cut 711. Weighted-degree orderings are worse by these proxies
(span 17,828–17,880; maximum cut 745–765). Fiedler/RCM/min-fill remain future
bounded candidates; none has yet earned an HPC slot.
The Fiedler probe improved the proxy (span 15,854; maximum weighted cut 647)
and the tensor run (67.49 s and discarded weight 125.49), but still used 31,108
swaps and agreed with the original modal bits at only 15/36 positions. It is
promising for another Mac-only control, not for HPC. The follow-up bond-128
Fiedler rung did not complete within its 180-second wall guard and is recorded
as a bounded timeout, so higher bond capacity is not currently justified.

## 6. Does tensor-aware routing help?

The original lookahead-4 probe failed immediately because the planner assumed
identity layout. A targeted, hash-recorded fix passed a bond-32 smoke test and
enabled the Fiedler lookahead-4 route. At bond 64 it reduced swaps from 31,108
to 11,316 and runtime from 67.49 s to 33.73 s; an independent seed reproduced
the route telemetry and completed in 31.37 s. However, the same configuration
failed the P9 positive-control gate at bond 64/cutoff 0.01: the post-hoc P9
predicted bitstring had Hamming distance 26/56 and discarded weight 190.72.
The bounded cutoff follow-up at 0.002 also failed, with Hamming distance
28/56, discarded weight 197.11, and the same 23,420 swaps. This is a useful
Mac throughput result, but not an HPC promotion or a correctness result.

## 7. Does low-bond distillation reveal stable bits?

Native MettleQ MPS is now available after installing MLX 0.32.2 into the external
environment. Three blind runs at bond 64 and cutoff 0.01 completed in 73.87–77.09
s. All hit the bond ceiling; cumulative discarded weight was 131.59–136.76, with
31,108 routing swaps each. The weighted-degree ordering took 75.83 s and had
discarded weight 132.44, so it did not improve the trajectory. Across all three
runs only 11/36 modal bits agreed, the mean pairwise marginal difference was
0.2530, and no bit was ≥0.90 on the same side in all runs. The result is
therefore unstable and is not promoted as correctness. A controlled cutoff
comparison at `0.002` versus `0.01` also failed: discarded weight was 132.41
versus 131.59, routing swaps were unchanged, and the mean marginal difference
was 0.2728. The independent Aer fallback also produced 1,000 unique samples.
Full evidence is in
`results/bluequbit_p1/distillation/CONSENSUS.json`.

## 8. Latent correspondence

The local-unitary/mirror scan shows high raw optimized scores, but its null is a
fixed random-permutation baseline and is not a fair optimized-matcher null. The
fairer sequence matcher remains weak and unstable under a larger control: with
32 shuffled trials and four restarts, the best z-scores were 2.88 (window 64,
empirical p=0.061), 2.60 (window 128, p=0.061), and 3.07 (window 256,
p=0.030), while neighboring-window permutation stability was only 0.0463.
The best mismatched-window scores were close to the matched scores. This is
insufficient evidence for explicit permutation recovery or a KAK/Makhlin
implementation.

## 9. Rejected hypotheses

Reject, for now: “P1 is solved by changing complex64 to complex128”; “more bond
dimension or a tighter cutoff alone fixes the problem”; “the 97–99% terminal claim is reproduced”;
“raw mirror z-scores prove a hidden inverse”; and “weighted interaction
frequency is graph degree.”

## 10. HPC shortlist

The shortlist remains intentionally empty. The required Mac evidence gate has
not been met: the MPO run timed out early, and although Fiedler/lookahead-4 is
reproducible on P1, it fails the same-method P9 control at both tested cutoffs
(26/56 at 0.01 and 28/56 at 0.002).
The manifest records that state. No HPC job has been started.

## Executed and intentionally not executed

Executed: input-only P1/P9 statistics, P1 structural/mirror scan, P1 sequence
scan with shuffled controls, P1 local-unitary scan, one bounded complex64 MPO
run, one bounded Aer MPS fallback, three native MettleQ MPS runs with
independent ordering/routing seeds, and P9 calibration runs at cutoffs 0.01
and 0.002 for the lookahead-routing probe. Existing
non-hardware tests pass: 149 passed in
36.30 seconds.

Not executed: BlueQubit cloud submission, Quantinuum/QPU submission, real HPC
jobs, answer-guided P1 tuning, unbounded Mac sweeps, explicit KAK/Makhlin
recovery, and any modification to frozen P9/P11 conclusions. The external
MettleQ routing patch is documented in
`docs/BLUEQUBIT_P1_METTLEQ_PATCH.md` and
`hpc/solver_patches/mettleq_initial_layout.patch`.

**Decision:** do not promote any current configuration to HPC. The current
ordering/routing screens reject weighted-degree initialization and lookahead-4
routing; bond-128 Fiedler timed out under the Mac budget. The P9 calibration
also rejects lookahead-4 as a general-purpose solver configuration. The empty
HPC manifest is therefore intentional and no cloud, QPU, or HPC submission was
made.
