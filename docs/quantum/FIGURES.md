# Reproducible figures

Generate the figures offline with:

```bash
.venv/bin/python tools/generate_quantum_figures.py
```

The script reads only committed machine-readable evidence: canonical P11/P12
shots, P12 analysis JSON, and the retained P12 cost ladder. It produces:

- [`collision_structure.png`](figures/collision_structure.png)
- [`p12_candidate_comparison.png`](figures/p12_candidate_comparison.png)
- [`p12_cost_ladder.png`](figures/p12_cost_ladder.png)
- [`evidence_flow.png`](figures/evidence_flow.png)

The plots contain no invented error bars or unrecorded timing/error estimates.
