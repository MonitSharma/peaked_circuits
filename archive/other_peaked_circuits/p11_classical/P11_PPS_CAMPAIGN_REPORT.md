# P11 classical PPS campaign report

## Executive result

Terminal state: `NO_GO_PPS_P9_SMOKE`. The independent PauliPropagation.jl path was staged and its gate adapter was validated, but the campaign did not pass the P9 control. P11 was therefore not run. The current evidence supports stopping here and reviewing the PPS representation/truncation strategy before asking for more hardware.

## What worked

- Julia 1.10.10 was installed user-locally on the HPC server.
- PauliPropagation.jl was installed at the requested exact commit.
- Canonical P9/P11 gate streams and structural audits were generated.
- Dense Qiskit validation passed for native and generic gates.
- The P9 `1e-3` smoke completed in about 26 seconds wall time at 18 Julia threads and about 588 MiB peak RSS.
- The prescribed Julia test command passed 8 tests, and the existing Python non-hardware baseline passed 146 tests in 61.15 seconds.
- Thread scaling on a fixed 200-gate P9 prefix was deterministic at 1, 4, 8, and 18 threads. The 8-thread run was marginally fastest internally; external maximum RSS was below 0.5 GiB for this short prefix.

## What failed

At `1e-3`, every P9 smoke observable was truncated to an empty sum, yielding zero expectation and an explicitly unresolved sign. At `1e-4`, the first representative observable did not finish within a bounded 125-second probe, produced no result file, and reached multi-GiB RSS. Therefore the required stable P9 signal was not recovered.

No full 56-observable P9 campaign was authorized, and no P9 accuracy table exists beyond the fixed smoke panel. No P11 bounded probe or full P11 marginal run was authorized.

The likely failure mode is representation growth from treating the 3,890 arbitrary one-qubit U gates as exact generic transfer maps combined with a threshold that removes the surviving signal. This is a computational/algorithmic failure of the tested path, not a proof that a different exact classical method or stronger machine cannot solve P11.

## Reproducibility artifacts

See `results/p11_pps_campaign/` for structural audits, gate streams, validation inputs, P9 smoke outputs, and the aborted convergence record. Existing unrelated HPC artifacts remain untouched.

## Blindness statement

No P11 answer, candidate, external scorer, or P11-specific online search was used. P11 execution count is zero.

## Supported and unsupported claims

Supported: the adapter is machine-precision correct on the tested small circuits; the package can run a bounded P9 prefix reproducibly; the tested full-circuit PPS truncation settings did not produce a trustworthy P9 signal within the prescribed resource boundary. Unsupported: classical impossibility of P11, a claim that more hardware would never help, or any P11 correctness claim.
