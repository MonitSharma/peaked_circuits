# P11 classical HPC runbook

This branch prepares, but does not execute, the expensive P11 campaign on a Mac. The campaign is Linux-only and intentionally P11-blind: the P11 launcher always passes an empty expected bitstring and records no answer oracle.

## First run on a fresh Linux clone

```bash
git clone -b p11_classical https://github.com/MonitSharma/p12-helios-recovery.git
cd p12-helios-recovery
bash hpc/start_p11_campaign.sh
```

The first run creates `.venv-hpc`, fetches the pinned solver and QASM source, applies the checked-in solver patch, discovers hardware/NUMA/BLAS state, then starts the resumable orchestrator in `results/p11_hpc/<UTC timestamp>/`.

Monitor with `bash hpc/status.sh`. Stop safely with `bash hpc/stop_campaign.sh`; resume a stopped campaign with `bash hpc/resume_campaign.sh`. Package compact results with `bash hpc/package_results.sh <campaign-dir> <archive.tar.gz>`; tensor checkpoints are excluded by default.

The orchestrator runs P9 calibration first at 18, 36, and 72 physical-thread profiles. It selects a measured profile only after a 56/56 P9 reproduction. It then records H1 high-bond P11 trajectories at D1024/D2048/D4096, gates the real MPO pair-lookahead beam on P9, and only then launches P11 horizons. D6144 is deliberately not automatic.

If a node lacks `numactl`, the launcher falls back to direct execution while preserving the discovered hardware record. If the solver import or P9 gate fails, the state is retained with an explicit failure status rather than advancing to P11.
