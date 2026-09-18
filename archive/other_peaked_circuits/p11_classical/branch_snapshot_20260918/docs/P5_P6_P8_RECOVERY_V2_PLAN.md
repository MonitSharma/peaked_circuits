# P5/P6/P8 Recovery V2 Plan

> **Planning snapshot; superseded 2026-08-31.** The protocol and blindness
> requirements remain useful, but the status and next-action recommendations
> below predate the newer P6/P8 experiments. See
> [P6_P8_REASSESSMENT_20260831.md](P6_P8_REASSESSMENT_20260831.md) for the
> current evidence.

This branch is the authoritative local classical campaign for P5, P6, and P8.
The initial evidence is frozen under `results/expert_review_p5_p6_p8_20260828/`.
The three QASMs are hash-identified and never rewritten.

The scientific priority is P5 → P6 → P8. P5 receives an answer-blind ensemble
and joint completion decoder; P6 is rebuilt from weighted interaction structure
and the calibrated MPO/unswapping path; P8 is treated as a sparse-geometry
problem, with TTN/graph-TN controls preceding any production promotion.

Recovery modules cannot read expected answers, overlap scores, portal feedback, or
hardware results. Candidates are frozen and hashed before evaluation. P9 is the
sole positive-control exception for calibrating bit order and the official MPO
path.

All heavy runs are local, serialized, four-thread bounded jobs with process-tree
RSS, swap, child-count, wall-time, and numerical-failure guards.
