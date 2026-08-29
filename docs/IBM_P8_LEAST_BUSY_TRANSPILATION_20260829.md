# P8 IBM least-busy transpilation diagnostic

No IBM job was submitted. The authenticated IBM account was queried for the
least-busy operational non-simulator backend with at least 40 qubits, and P8
was transpiled at optimization level 3 for the selected backend.

- Source QASM SHA-256: `ba42c338478fdfbc0241ec2289b3159bfde5dffc71603ac588ec0755fba1a484`
- Selected backend: `ibm_fez`
- Backend width: 156 qubits
- Pending jobs at selection: 3
- Logical circuit: 40 qubits, depth 130, 888 two-qubit gates
- Transpiled circuit: 156 qubits, depth 2,052, 4,044 two-qubit gates
- Depth overhead: 15.78x
- Two-qubit-gate overhead: 4.55x
- Selection rule: minimum pending jobs among operational non-simulators with
  at least 40 qubits, with backend name as tie-break

The P8 grid is structurally sparse, but its 888 two-qubit operations still
expand substantially on IBM connectivity. This transpilation is therefore a
useful hardware diagnostic, not evidence that an IBM run will preserve a
recoverable peak. The transpiled circuit and complete metadata are preserved
under `results/ibm_p8_transpile_20260829/`.
