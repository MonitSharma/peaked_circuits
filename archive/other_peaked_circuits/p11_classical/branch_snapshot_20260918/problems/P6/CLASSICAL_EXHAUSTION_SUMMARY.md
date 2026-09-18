# P6 classical exhaustion summary

**Normalized outcome: `UNRESOLVED`**

Within the tested method families and available local computational resources,
the P6 classical campaign did not produce a defensible blind candidate. The
campaign is best described as method-exhausted for this implementation and
resource envelope, not as classically impossible.

## The measured transition

| Regime | Observed behavior | Scientific meaning |
|---|---|---|
| D512, cutoff `6e-4` | faithful runs stall around 138–150 work gates | routing and entanglement coupling blocks progress |
| cutoff `1.875e-3` | 2,593/2,593 completed; peak fraction about 0.001 | traversal completed after signal was lost |
| cutoff `2e-3` | 2,593/2,593 completed; top1/top2 about 1.02–1.06× | same flat-readout failure |

The endpoint reports and detailed diagnosis remain the authoritative numerical
records. A completed gate counter is not a fidelity result.

## What remains open

The most plausible future directions are structural reconstruction that avoids
the line-MPO wall, or a separately controlled candidate-adjudication protocol.
The supplied overlap references may be used only after candidate generation as
oracle-assisted analysis; they must not tune a blind search.
