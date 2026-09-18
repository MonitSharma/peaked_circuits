# Problem archive

This directory is the problem-oriented index for P1–P11. Each problem folder
contains a README describing the question, methods, resources, timing, and
current evidence, plus an `ARTIFACTS.md` manifest pointing to the canonical
files elsewhere in the repository.

The first organization pass is intentionally non-destructive: existing result
directories are not moved or duplicated, so historical scripts and reports
retain their paths. New experiments should be placed under the relevant
`results/` problem directory and added to that problem's manifest.

| Problem | Current evidence status | Folder |
|---|---|---|
| P1 | Methods exhausted; no converged blind candidate | [P1](P1/) |
| P2 | Historical portal/distillation artifacts; audit pending | [P2](P2/) |
| P3 | Historical portal/distillation artifacts; audit pending | [P3](P3/) |
| P4 | Historical portal/distillation artifacts; audit pending | [P4](P4/) |
| P5 | Positive known-answer control; recovery artifacts retained | [P5](P5/) |
| P6 | Completed loose-cutoff runs are flat; no verified answer | [P6](P6/) |
| P7 | Historical portal/distillation artifacts; audit pending | [P7](P7/) |
| P8 | Tail materialization produced the recorded 40/40 result | [P8](P8/) |
| P9 | Positive known-answer control; multiple validated settings | [P9](P9/) |
| P10 | Historical portal/distillation artifacts; audit pending | [P10](P10/) |
| P11 | Local classical methods exhausted; no blind candidate | [P11](P11/) |

Shared calibration, infrastructure, and cross-problem methodology remain under
`docs/`, `src/`, `scripts/`, and `results/` until a later archival pass moves
them safely.
