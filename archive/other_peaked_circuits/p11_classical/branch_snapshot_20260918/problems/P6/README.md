# P6 — titan pinnacle

## Status

`NONCONVERGED`: no verified answer. The `1.875e-3` run completed all 2593
gates but produced a flat readout, like the completed `2e-3` runs. The bounded
Pilot-Wave feasibility probe is also closed: its reference greedy planner
took 29.9 seconds for only 250 source operations and exceeded one minute at
500 source operations, before any P6 sampling.

## Methods and resources

Tested faithful and loose-cutoff MPO compression, `flip_freq`, route candidates,
balanced scheduling, tabu/cycle memory, D128 sampling, structural unitary and
patch matching, backbone ordering, and fixed-candidate amplitude feasibility.
Resources included the local MPO solver, Quimb/Qiskit, structural modules,
QASM inputs, and bounded CPU runs.

## Timing and evidence

The completed `1.875e-3` run took roughly 2.5 hours of compression and reached
2593/2593, but its 1000 samples were all unique with peak fraction 0.001. Exact
run telemetry and every candidate family are linked below. Supplied overlap
labels remain post-hoc references.

## Canonical records

See [ARTIFACTS.md](ARTIFACTS.md) and the detailed diagnosis.

## Classical closure statement

The project has effectively exhausted the credible classical routes tested
within the available representations and resource envelope. This does not
prove universal classical impossibility. The next planned route is execution
on refreshed HQC/Quantinuum hardware.
