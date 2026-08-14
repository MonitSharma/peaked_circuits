# Mac MPO workflow

This is the recommended first environment for optimizing the peaked-circuit
CPU simulation. It uses the same public CPU MPO + greedy-unswapping solver as
the server workflow, but keeps the Mac environment separate from the main
P12 recovery environment.

## First setup

From the repository root on macOS:

```bash
bash scripts/setup_mac.sh
source .venv-mpo-mac/bin/activate
```

The setup script creates the main `.venv` environment, the separate
`.venv-mpo-mac` environment, installs their dependencies, and clones the
solver into `vendor/peaked-mpo-solver` if needed. It does not submit hardware
work or start a long simulation.

Do not copy a Linux or Windows virtual environment to the Mac. Virtual
environments contain platform-specific binaries.

## Confirm the numerical stack

```bash
python -c "import platform,sys; print(platform.platform()); print(platform.machine()); print(sys.version)"
python -c "from threadpoolctl import threadpool_info; import numpy; print(threadpool_info())"
git -C vendor/peaked-mpo-solver rev-parse HEAD
```

The BLAS output matters because the QAT Mac results used a highly optimized
Mac linear-algebra stack. Keep the output with each benchmark result.

## Reproducible P9 smoke benchmark

Run the two bounded tests:

```bash
bash scripts/benchmark_p9_mac.sh
```

This compares four and eight BLAS/Numba threads over 300 work gates. It uses
P9 because the expected bitstring is known and the run is a practical
regression test. A valid result should report `matches_expected_bitstring:
true`.

Do not assume that more threads are faster. For this solver, SVD, tensor
allocation, and greedy unswapping can scale poorly. Test a small number of
thread budgets and retain the complete `summary.json` files.

## Full P9 benchmark

After the smoke test, use the faster thread count for a full run. For example:

```bash
python scripts/run_peaked_mpo_cpu.py \
  --solver-root vendor/peaked-mpo-solver \
  --threads 8 \
  --qasm vendor/peaked-mpo-solver/circ/peaked_circuit_P9_Hqap_56x1917.qasm \
  --outdir results/simulation \
  --tag p9_mac_full \
  --samples 1000 \
  --cutoff 0.0006 \
  --no-parallel-rewire \
  --expected-bitstring 01101110111001100000100000001010011100101101010111110111
```

## P12 policy

Do not launch an unbounded P12 run as the first Mac experiment. First compare
short, separately tagged runs:

```bash
python scripts/run_peaked_mpo_cpu.py \
  --solver-root vendor/peaked-mpo-solver \
  --threads 8 \
  --qasm circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm \
  --outdir results/simulation \
  --tag p12_mac_cutoff_001 \
  --max-work-gates 100 \
  --samples 0 \
  --cutoff 0.001 \
  --abort-after-no-progress-unswap-cycles 10 \
  --no-parallel-rewire
```

Repeat with cutoffs `0.0015` and `0.002`, changing only the tag and cutoff.
Compare elapsed time per work gate, maximum bond, tensor element count,
forced-drain warnings, and termination reason before considering a longer run.

## What to report

For each run, record the Mac model, Python version, solver commit, QASM path,
thread budget, cutoff, `termination_reason`, `compress_time_s`, maximum bond,
peak tensor elements, and P9 bitstring match status. These fields allow Mac
and Intel-server results to be compared without confusing configuration
changes with hardware performance.
