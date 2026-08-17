# Tools Directory

This directory contains standalone CLI tools and analysis utilities for benchmarking, optimizing, and verifying classical quantum tensor network simulations (particularly for P9 and P11 circuits).

---

## Tool Overview

| Script | Purpose |
| :--- | :--- |
| [`run_p9_mettleq.py`](./run_p9_mettleq.py) | Executes the MettleQ MPS prefix engine with configurable bond dimension, compression cutoff, and thread allocation. |
| [`benchmark_svd_methods.py`](./benchmark_svd_methods.py) | Benchmarks tensor truncation methods (`svd`, `rsvd`, `isvd`, `svds`) across dimensions and precisions. |
| [`summarize_p9_results.py`](./summarize_p9_results.py) | Aggregates contraction dynamics, failure rates, and wall-time across multiple run directories into summary CSVs. |
| [`verify_p9_results.py`](./verify_p9_results.py) | Validates candidate bitstrings and checks simulation fidelity against expected constraints. |
| [`plot_p9_submission.py`](./plot_p9_submission.py) | Generates publication-ready plots for contraction dynamics, bond growth, and SVD method performance. |
