# P5/P6/P8 Overnight Runbook

> **Historical runbook — superseded 2026-08-31.** The original portfolio
> resume command below is retained for provenance but must not be used as a
> blind retry of rejected stages. Current results and next actions are in
> [P6_P8_REASSESSMENT_20260831.md](P6_P8_REASSESSMENT_20260831.md).

Dry-run state inspection:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_peak_recovery_portfolio.py --resume
```

Bounded execution, one heavy process at a time:

```bash
caffeinate -i nice -n 10 env PYTHONPATH=src .venv/bin/python \
  scripts/run_peak_recovery_portfolio.py --execute --resume \
  --night-budget-hours 7 --threads 4 --rss-soft-gb 20 --rss-hard-gb 24 \
  --swap-growth-limit-gb 2 --cooldown-minutes 5
```

The controller is resumable. It must stop or demote methods when their control,
resource, numerical, or convergence gates fail. It must never submit hardware or
cloud work. Before any target evaluation, create a candidate freeze artifact and
record its hash, settings, QASM hash, and repository commit.

The 2026-08-29 checkpoint and its TTN/graph-TN recommendation are superseded.
The current P6 action is a completed cutoff bisection around `1.5e-3`--
`1.875e-3`, followed by an adaptive rescue only if calibration permits it. The
current P8 action is a clean replay of the historical 804/808 controller
trajectory followed immediately by tail materialization. Both require the
safe `p9-openblas` environment and a writable Numba cache.
