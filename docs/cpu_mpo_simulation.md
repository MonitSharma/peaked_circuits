# CPU MPO simulation

This project now has a launcher for the public CPU-oriented implementation from
[`alexgalda-m/peaked-mpo-solver`](https://github.com/alexgalda-m/peaked-mpo-solver).
That implementation uses midpoint matrix-product-operator (MPO) compression and
greedy unswapping. It is the code reported in QAT issue [#153](https://github.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io/issues/153).

## Install on the CPU server

Use a separate environment because the solver pins a numerical stack that is
different from the recovery pipeline's validation stack:

```bash
git clone --depth 1 https://github.com/alexgalda-m/peaked-mpo-solver.git vendor/peaked-mpo-solver
python3 -m venv .venv-mpo
source .venv-mpo/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The launcher injects the solver checkout through `PYTHONPATH`; it does not
submit jobs or contact a quantum device.

## Probe and run

First collect machine information:

```bash
python scripts/probe_cpu_server.py --output results/cpu_server_probe.json
```

This server has 72 physical cores across four NUMA nodes. Start with one
NUMA-sized budget, then compare 36 and 72 physical cores; SMT threads are not
automatically better for the large SVDs in this solver.

For the 98-qubit P12 circuit, start with a bounded smoke run so memory and
runtime are known before committing to a complete run:

```bash
python scripts/run_peaked_mpo_cpu.py \
  --threads 18 \
  --max-work-gates 250 \
  --samples 0 \
  --cutoff 0.0006 \
  --no-parallel-rewire
```

If the smoke run is healthy, remove `--max-work-gates` and use the same command
with `--samples 1000` for a complete ideal-circuit sampling run. On a server,
the first tuning knob is `--threads`; do not increase it blindly because nested
BLAS/Numba parallelism can make a many-core machine slower.

The launcher writes `cpu_launcher.json` next to the solver's run artifacts. For
P12 it disables the upstream P9 expected-bitstring comparison by default. A
successful run should be judged by `termination_reason: completed`, peak
stability, and resource usage; P12 currently has no locally known expected
bitstring in this repository.

## What “bigger” means here

The QAT P9 CPU result is for 56 qubits and 1,917 `rzz` gates. This repository's
P12 instance is 98 qubits and 2,457 `cz` gates, while QAT's P11 instance is also
98 qubits and 1,999 gates. The solver's core path is dimension-independent, but
linear routing and MPO bond growth can make the larger instances much harder
than the gate-count ratio suggests. A complete P12 simulation is therefore a
research trial, not a guaranteed extrapolation of the 12-minute P9 result.

Record the solver version, QASM hash, cutoff, max bond, unswap threshold,
thread budget, peak counts, and termination reason for every comparison.
