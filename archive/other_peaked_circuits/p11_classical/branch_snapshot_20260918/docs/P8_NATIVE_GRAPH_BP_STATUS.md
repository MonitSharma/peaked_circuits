# P8 native-graph 2-norm BP pilot

This pilot implements the requested method: the original native iSWAP circuit is evolved on its 40-node interaction graph, with virtual bonds only on the 63 native interaction edges. iSWAP is applied directly to the two endpoint tensors. The local post-gate split is kept exact; Quimb's 2-norm belief-propagation compressor performs the environment-aware truncation afterward.

The implementation is in `src/p12_recovery/peak/native_graph_state.py` and is driven by `scripts/run_p8_native_graph_bp.py`. One-qubit U3 gates do not trigger a BP solve because they cannot change virtual bond structure. Product-state rank-one bonds are skipped because a BP gauge has no nonzero environment to condition in that state.

## Controls and bounded P8 prefix

The isolated HPC environment used was `.venv-mpo-py310`; the fragile `p9-openblas` environment was not modified. The original P8 QASM has 2,704 events, 888 iSWAPs, 40 qubits, and 63 native edges.

For the first 100 events:

| chi | final norm | observed max bond |
|---:|---:|---:|
| 4 | 0.5664754208 | 4 |
| 8 | 0.9705696303 | 8 |
| 16 | 1.0000000000 | 16 |
| 32 | 1.0000000000 | 16 |

The chi=4 300-event prefix completed in 66.5 seconds but its norm fell to 0.0377589228. The chi=8, 16, and 32 300-event jobs were stopped after BP calls exceeded the bounded wall-time expectation; they did not produce result files. This is a feasibility warning, not a P8 answer.

## Current conclusion

The method is technically viable on nontrivial small controls and remains finite at chi 4--32 on the 100-event P8 prefix. However, low chi is decisively lossy, while the higher-chi BP cost rises sharply. No chi=64 run is justified: the monotonic diagnostic gate is not met on the available full-prefix data, and no candidate bitstring is being claimed.

Saved diagnostics are under `results/p8_native_graph_bp/`.
