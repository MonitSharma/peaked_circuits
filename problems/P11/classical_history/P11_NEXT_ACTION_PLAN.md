# P11 next action plan

## Decision

Run a small, instrumented calibration pilot on NUMA node 0 now. Do not wait for more
resources for that pilot. Wait for additional NUMA capacity before launching the full cutoff
ladder, concurrent sweeps, or any claim about multi-node throughput.

Only NUMA node 0 is currently free. The host has four NUMA nodes, 72 physical cores, and about
503 GiB RAM, but the free capacity of one node must be measured rather than inferred. Treat the
available node as an isolated experimental slot, not as permission to use the other nodes.

## Why this is the right split

The P11 telemetry changes the bottleneck diagnosis:

- R3 at cutoff `2e-3`, bond `4096`, stopped at 78 work gates under the wall cap.
- R4 at cutoff `5e-3`, bond `4096`, completed all 1,984 work gates in about 51 minutes.
- R4 peaked at bond 605, with zero rows at the 4096 ceiling.
- The blind R4 sampling run completed, but all 1,000 samples were unique (`1/1000` modal count).

This is a fidelity/throughput frontier. More RAM alone is not yet an evidence-backed solution.

## Stage 0 — node-0 pilot

Before running a ladder:

1. Record `numactl --hardware`, free memory on node 0, CPU availability, BLAS thread settings,
   solver commit, Python environment, and the exact command.
2. Pin one process to node 0 and one physical core first. Keep OpenBLAS/NumPy at one thread.
3. Run a short P9 control prefix and compare progress, bond, truncation diagnostics, and RSS
   with the known Mac reference.
4. Run the corresponding short P11 prefix with an empty expected bitstring. Do not inspect or
   derive a P11 target.
5. Stop if RSS, swap, numerical warnings, or routing trajectories depart materially from the
   preregistered baseline.

The pilot answers whether node 0 is operationally usable. It does not answer whether the HPC
implementation reproduces P9 or whether P11 is solvable.

## Stage 1 — P9 cutoff frontier

After Stage 0 is clean, run P9 at cutoffs `2e-3`, `2.5e-3`, `3e-3`, `3.5e-3`, `4e-3`, `4.5e-3`,
and `5e-3`, keeping routing, seed, bond ceiling, and decoder fixed. Each rung must record:

- exact P9 recovery status and Hamming distance;
- runtime and work-gate completion;
- peak bond, truncation diagnostics, process-tree RSS, and swap use;
- sample concentration and decoder output;
- complete command and environment provenance.

P9 recovery is the gate. If the exact control fails, stop and repair the implementation or
conventions before running P11.

## Stage 2 — P11 frontier

Only after P9 passes, run the same cutoff ladder on P11 with a multi-day wall budget if the
allocation permits. Keep the run blind (`--expected-bitstring ""`). For each rung, record full
completion, work-gate progress, wall time, peak bond, truncation diagnostics, RSS, and the
distributional diagnostics. Do not call a diffuse blind sample a recovery.

The useful result is the interval between:

- the loosest cutoff at which P9 still recovers exactly; and
- the tightest cutoff at which P11 completes within the agreed wall budget.

If the intervals do not overlap, report a quantitative no-go for this MPO-plus-unswapping
configuration. If they overlap, run the overlap with independent seeds and a preregistered
stability test.

## NUMA scheduling recommendation

With only node 0 free, use one conservative process for calibration. Do not start 16–24 jobs:
that requires the other nodes and would contaminate the resource boundary. When more capacity
is free, begin with four independent single-threaded jobs, one per node, at roughly measured
working-set size. Increase concurrency only after RSS, NUMA placement, wall time, and P9 output
are stable. The solver's poor many-thread scaling makes independent single-threaded jobs more
plausible than one large multithreaded process, but this remains an experiment to validate.

## Open methods after the frontier

The official repository's TNO contraction and official distillation algorithm remain untested
and must not be described as closed. The latter is distinct from the project's low-bond MPS
distillation. Full-network contraction at width `2^202` remains out of scope.

## Stop conditions

Stop and preserve artifacts if P9 fails, if a run uses swap, if RSS approaches the node limit,
if numerical warnings change the trajectory, or if any analysis would require a P11 target or
verifier that is not independently supplied. No external M3 Ultra or GPU rental is justified
until these gates produce evidence that the new method needs it.
