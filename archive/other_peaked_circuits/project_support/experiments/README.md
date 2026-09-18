# Experiments & Local Run Sweeps

This directory is the dedicated workspace for classical solver parameter sweeps, local MPO / MPS execution trials, and simulation checkpoints.

## Directory Structure

- `runs/`: Contains individual sweep output folders (e.g. `cutoff*`, `mps_*`, `layer_*`, `lazyproxy_*`, `maxbond256_*`, `threshold*`, etc.).
  - *Note: `runs/` is git-ignored by default to prevent large simulation logs and tensor network checkpoints from bloating repository history.*

## Distilled Findings

- All validated summary metrics and distilled analysis from these runs are archived in [`../results/`](../results/):
  - **P9 Benchmarks & Contraction Optimization**: [`../results/p9_optimization/`](../results/p9_optimization/)
  - **P11 Routing & Entanglement Diagnosis**: [`../results/p11_diagnosis/`](../results/p11_diagnosis/) and [`../docs/P11_ROUTING_DIAGNOSIS.md`](../docs/P11_ROUTING_DIAGNOSIS.md)

## Running Sweeps

To execute new parameter sweeps into this directory, specify an output path under `experiments/runs/`:

```bash
python scripts/run_p11_mpo.py \
  --qasm circuits/p11.qasm \
  --outdir experiments/runs/p11_sweep_example \
  --threads 6
```
