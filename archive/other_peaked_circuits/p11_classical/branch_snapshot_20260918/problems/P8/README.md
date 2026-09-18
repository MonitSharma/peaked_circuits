# P8 — grid 888 iSWAP

## Status

The recorded tail-materialization route produced the known 40/40 result from
the 804/808 checkpoint. The result is preserved with its provenance caveats in
the P8 forensic and candidate reports.

## Methods and resources

Tested MPO routing, `flip_freq`, balanced scheduling, tabu/cycle memory, real
tail beams, native-iSWAP framing, graph/TTN/PEPS controls, and final MPO-to-MPS
tail materialization. Resources included the P8 QASM input, local solver
patches, Quimb/Qiskit, and bounded Mac/conda runs.

## Timing and evidence

The promoted tail result reports peak fraction 0.038, decoder top-1 about
0.029, and top-1/top-2 about 6.44x. The exact runtime and provenance are in the
linked candidate artifact.

## Canonical records

See [ARTIFACTS.md](ARTIFACTS.md).
