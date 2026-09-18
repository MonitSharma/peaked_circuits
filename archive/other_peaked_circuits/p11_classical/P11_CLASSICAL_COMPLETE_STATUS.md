# `p11_classical` — Complete P9/HPC Status and P11 Next-Step Report

**Date:** 2026-08-27  
**Branch:** `p11_classical`  
**Purpose:** Record the complete reproducibility work, failed attempts, verified P9 reference, and the recommended path toward a classical P11 attempt.

## Executive conclusion

P9 is scientifically solved on the MacBook, but it is **not yet reproduced on the HPC server**.

The HPC pipeline was repaired enough to complete the full P9 traversal. However, its final modal bitstring was wrong. The server completed all 1,885 consolidated work gates and produced a strong peak, but that peak differed from the canonical P9 peak in 18 of 56 bits.

This means:

- The HPC environment and process execution are functional.
- The current CPU implementation is not equivalent to the validated MacBook/reference implementation.
- The failure is algorithmic/numerical/protocol divergence, not an out-of-memory failure.
- P11 must remain frozen until the exact P9 control reproduces successfully on the target platform.

## Canonical P9 answer

The verified P9 peak is:

```text
01101110111001100000100000001010011100101101010111110111
```

The public authors' notebook records this as `true_bs`, obtains it as the permuted modal sample, and checks `perm_pred_bs == true_bs`. In the displayed 1,000-sample run, the peak occurred 106 times.

- [Public reference notebook](https://raw.githubusercontent.com/d-kremer/peaked-circuit-simulation/refs/heads/main/peaked-circuit-unswapping.ipynb)
- [Quantum Advantage Tracker verified submission #106](https://github.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io/issues/106)

The Tracker submission reports the reference P9 run on one NVIDIA A100 80GB GPU in 4,059 seconds.

## What was done

### Repository and branch

- Switched the local repository to `p11_classical`.
- Confirmed the branch history and pushed the work to GitHub.
- Current relevant branch commits include:
  - `dec79c4` — prior HPC follow-up report and branch state.
  - `2bcaf05` — aligned the HPC P9 calibration wrapper with the Mac protocol defaults.

### HPC transfer and host audit

The repository was transferred to the HPC host:

```text
Host: LHC-104-070
Remote: /home/hclau/p12-helios-recovery
```

Host audit:

- Ubuntu 24.04.4
- 144 logical CPUs / 72 physical cores
- 4 sockets / 4 NUMA nodes
- Intel Xeon Gold 6154
- Approximately 503 GiB RAM
- 8 GiB swap, unused during the runs
- No material memory pressure was observed

The HPC run was pinned conservatively to one NUMA node and 18 physical CPUs initially. Later testing showed that one thread was substantially more efficient for this solver because large SVDs and nested BLAS parallelism scaled poorly.

### Environment setup

The project and solver require incompatible Python ranges, so two environments were created:

```text
Project environment: .venv-hpc
Python: 3.12.3

Solver environment: .venv-mpo-py310
Python: 3.10.21
```

The solver environment uses the declared Python 3.10-compatible dependency stack and the solver checkout with the QR compatibility guard.

This split is required because:

- The project code uses Python 3.11+ APIs such as `datetime.UTC`.
- The external MPO solver declares Python `>=3.10,<3.11`.

The project environment passed the existing non-hardware test suite: 146 tests passed. The solver environment imported and executed the P9 CLI successfully.

## HPC P9 attempts

### 1. Initial Python 3.12 HPC retry — invalid solver environment

The first HPC retry used Python 3.12.3 even though the solver requires Python 3.10.

Observed result:

- Stopped after 15/1,885 gates.
- Approximately 198 seconds elapsed.
- About 1.1 GiB RSS.
- No swap use.
- No final result bundle.

This was an infrastructure/reproducibility failure and was not valid evidence about P9 or P11.

### 2. Correct Python 3.10, but diagnostic settings — still stalled

The next run used Python 3.10.21 but retained diagnostic settings:

- 18 threads;
- `max_bond=512`;
- `cutoff=0.0006`;
- `pair_lookahead` unswapping;
- early no-progress behavior.

Observed result:

- 15/1,885 gates after approximately 212 seconds.
- Quimb reported SVD non-convergence and fell back to SciPy `gesvd`.
- The run was stopped because it was not advancing.

This showed that the Python-version problem had been repaired, but the run still did not represent the MacBook protocol.

### 3. Protocol-aligned 18-thread smoke run — technically progressed, operationally too slow

The wrapper was then aligned with the MacBook/reference-style defaults:

- `max_bond=8192`;
- verified `bond` unswapping;
- `unswap_threshold=1e6`;
- 20-cycle no-progress limit;
- parallel rewiring disabled;
- explicit sample and work-gate controls.

The 18-thread configuration progressed, but only reached a handful of gates per minute. It was stopped because the many-core CPU/BLAS configuration was inefficient for this workload.

### 4. One-thread bounded probe — stable execution

A one-thread, one-NUMA-node probe was run with the aligned settings and a 15-gate work limit.

Observed result:

- Completed cleanly at 15/1,885 gates.
- Compression time: approximately 54.6 seconds.
- Peak bond during the probe: 256.
- Termination reason: `max_work_gates`.

This established that one-thread execution was the most stable CPU configuration tested on this host.

### 5. Full one-thread HPC P9 run — traversal complete, peak incorrect

The final full run used:

```text
Python: 3.10.21
Threads: 1
NUMA: one node
max_bond: 8192
cutoff: 0.0006
unswap_threshold: 1e6
unswap_select_mode: bond
parallel_rewire: disabled
samples: 1000
seed: 123
```

Observed result:

- Full traversal: 1,885/1,885 gates.
- Runtime: 4,915.8 seconds, approximately 82 minutes.
- `termination_reason`: `completed`.
- Peak bond: 1,024.
- Final bond: 16.
- Peak sample count: 93/1,000, approximately 9.3%.
- Memory remained safe; swap was unused.

The HPC modal bitstring was:

```text
01101111101001110001101111101000001100101100001111100000
```

It differs from the verified P9 peak in 18 of 56 bits. The result bundle therefore correctly reports:

```text
matches_expected_bitstring: false
```

The full run proves that the current server can execute the traversal. It does **not** prove that the current CPU implementation has recovered P9.

## Why the HPC result diverged

The HPC run was not the same computation as the verified public run.

### Routing search budget differed

The public notebook calls the unswapping routine without overriding its routing-search defaults. The reference implementation therefore uses a much larger Sabre search budget (`sabre_trials=10000`). The HPC CLI used approximately `sabre_trials=90` and `post_sabre_trials=50`.

That produces a different initial linear layout and different later rewiring decisions. The public notebook's initial routed layer counts and the HPC run's layer counts were different, demonstrating that the two runs entered different routing trajectories before sampling.

### Truncation cutoff differed

The verified public notebook uses `cutoff=0.002` for MPO compression and again for the final MPO-to-MPS conversion. The HPC run used `cutoff=0.0006`.

A smaller cutoff does not guarantee the same answer in this heuristic algorithm. Singular-value decisions affect greedy unswapping and subsequent rewiring, so changing the cutoff can change the entire computational path.

### Backend differed

The public reference uses Torch/CUDA on an NVIDIA A100. The HPC run uses CPU NumPy/SciPy/OpenBLAS. Near-degenerate SVDs can be ordered differently across numerical backends, and the greedy routing/unswapping procedure can amplify those differences.

### Implementation differed

The HPC run used the `p9solver` port/fork in this project, including HPC compatibility and telemetry changes. The public result was produced with the authors' `d-kremer/peaked-circuit-simulation` implementation and notebook. These are related implementations, but they are not byte-identical.

### Final permutation/MPS handling must still be audited

The public reference explicitly performs:

```python
mps, perm = mpo_to_mps(
    mpo,
    layers_left[:-2],
    layers_right,
    cutoff=0.002,
    to_backend=to_backend_cuda,
)
```

The HPC result contains a valid 56-qubit measurement permutation, so this is not yet proven to be a simple bit-reversal bug. However, the finalization and permutation convention must be compared directly against the reference implementation.

## Current scientific status

### P9

- MacBook: solved.
- Public reference: solved and verified.
- Current HPC CPU pipeline: full traversal completed, but incorrect peak recovered.

### P11

P11 remains an open computational target. No P11 result should be treated as credible until the exact implementation reproduces the known P9 control and then passes convergence and independent-validation checks on P11.

## Hardware interpretation

The current 503 GiB CPU server is not memory-limited for the completed P9 run. Its weakness is that the CPU implementation/backend does not match the validated MacBook or A100 path, and its SVD/routing performance is poor under the tested settings.

The most informative next experiment is a P9-calibrated software and cutoff study on the
available HPC host. The R4/R3 results do not justify treating memory capacity as the next lever.
An Apple-Silicon server or GPU allocation should be considered only after the exact reference
path and its P9 control have been reproduced, or when a new method demonstrably requires it.

If a later controlled hardware trial is justified, a possible target is:

- Apple M3 Ultra;
- 256 GiB unified memory;
- fast local storage;
- the exact MacBook software environment and solver;
- a bounded P11 prefix after P9 reproduction.

AWS currently lists an EC2 M3 Ultra Mac instance with 28 CPU cores, 60 GPU cores, and 256 GiB unified memory. EC2 Mac instances are bare-metal dedicated hosts and have a 24-hour minimum allocation period.

- [AWS EC2 Mac instances](https://aws.amazon.com/ec2/instance-types/mac/)
- [AWS EC2 Mac documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-mac-instances.html)

An A100/H100 GPU server remains appropriate if the exact reference implementation is CUDA/Torch-dependent. The public P9 reference used an A100 80GB, but that does not guarantee that P11 will fit in one GPU. P11 may require substantially more aggregate memory or a new distributed/multi-GPU implementation.

## Recommended next protocol

1. Freeze the MacBook P9 environment as the golden reference.
2. Record its exact solver commit, Python/package versions, command, seed, cutoff, max bond, and full result bundle.
3. Port the authors' public implementation itself to the HPC environment instead of continuing to tune the current `p9solver` port.
4. Match the public parameters exactly, especially:
   - `cutoff=0.002`;
   - `max_bond=8192`;
   - `unswap_threshold=1e6`;
   - `seed=123`;
   - `sabre_trials=10000`;
   - final MPO-to-MPS cutoff `0.002`.
5. Compare intermediate routing, bond, unswapping, and permutation checkpoints—not only the final bitstring.
6. Use the currently available NUMA node 0 for a small single-node calibration pilot; do not
   treat it as evidence for multi-node scaling.
7. Do not run a full blind P11 campaign or rent external hardware until P9 passes on the selected
   production platform and the cutoff frontier is measured.

## Final decision

The CPU server should be retained for development, diagnostics, and large-memory experiments. It should not yet be treated as the production platform for solving P11.

The lowest-risk next step is the gated NUMA-node-0 pilot described in
[`P11_NEXT_ACTION_PLAN.md`](P11_NEXT_ACTION_PLAN.md). Wait for more NUMA capacity before
launching parallel sweeps or interpreting throughput at scale. External M3 Ultra or A100/H100
spend remains conditional on a successful P9 reproduction and a result showing that the new
method—not simply additional RAM—is the limiting factor.
