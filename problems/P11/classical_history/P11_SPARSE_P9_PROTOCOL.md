# P9 sparse protocol

This is the preregistered P9 control protocol for the sparse campaign.

- Circuit: `data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm`.
- Methods: qstvec top-k, BASS fixed top-k, BASS adaptive top-k.
- Budgets: begin at `k=16384` and `k=65536`; consider `262144` and `1048576`
  only if the previous result is informative and resource-safe.
- Same Qiskit-derived canonical gate stream, complex128, initial zero state,
  deterministic seed, and logical output convention for every method.
- No concurrent heavy jobs.

For each run record target top-1/rank/presence/weight, top-1 Hamming distance,
rank gap, support and truncation trajectories, retained mass, participation
ratio, runtime, peak RSS, and complete provenance.

The preferred P9 gate is target rank 1 with stable or improving behavior as k
increases. A weaker condition requires explicit justification before result
inspection. BASS adaptive must materially beat BASS fixed at the same k to earn
an adaptive 98-bit port.

Known P9 information is used only as a calibration endpoint. No P11 answer or
external P11 correctness source is permitted.
