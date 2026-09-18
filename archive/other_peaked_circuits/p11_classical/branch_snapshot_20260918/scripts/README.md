# Scripts Directory

This directory contains execution scripts and workflow helpers for the P12 Helios Recovery pipeline and classical simulation experiments.

---

## Workflow & Pipeline Scripts

| Script | Purpose |
| :--- | :--- |
| [`setup_mac.sh`](./setup_mac.sh) | Sets up the main Python 3.11 virtual environment and installs development and quantum dependencies. |
| [`setup_mpo_mac.sh`](./setup_mpo_mac.sh) | Configures the isolated environment for the peaked MPO solver on macOS Apple Silicon. |
| [`benchmark_p9_mac.sh`](./benchmark_p9_mac.sh) | Runs the reproducible P9 MPO benchmark with memory and thread controls. |
| [`run_peaked_mpo_cpu.py`](./run_peaked_mpo_cpu.py) | Driver for running the peaked MPO CPU solver with resource bounds. |
| [`run_p11_mpo.py`](./run_p11_mpo.py) | Reproducible launcher for the P11 MPO + capped unswap solver with an active RSS watchdog. |
| [`parse_routing_trajectories.py`](./parse_routing_trajectories.py) | Parses run telemetry and produces consolidated summary and trajectory CSV datasets. |
| [`probe_cpu_server.py`](./probe_cpu_server.py) | Gathers host hardware specs, CPU features, BLAS backend status, and RAM availability. |
| [`compile_p12.py`](./compile_p12.py) | Triggers deterministic P12 target compilation. |
| [`validate_p12.py`](./validate_p12.py) | Validates circuit structure, qubit mappings, and logical ordering. |
| [`inspect_p12.py`](./inspect_p12.py) | Computes circuit depth, two-qubit gate count, and interaction graph topology. |
| [`fetch_p12.py`](./fetch_p12.py) | Verifies byte-level integrity of the upstream P12 QASM file. |
| [`build_readiness_report.py`](./build_readiness_report.py) | Assembles the final machine-readable readiness evidence report. |
| [`run_synthetic_benchmark.py`](./run_synthetic_benchmark.py) | Runs synthetic target benchmarks to validate statistical confidence. |
