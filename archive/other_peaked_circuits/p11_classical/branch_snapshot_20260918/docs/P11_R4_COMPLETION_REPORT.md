# P11 R4 completion report

## Result

The validated R4 configuration completed the full 1,984-gate P11 circuit on the
Apple Silicon host using the OpenBLAS environment:

| field | value |
|---|---:|
| cutoff | `5e-3` |
| max bond | `4096` |
| routing | 2 candidates, `lookahead_total`, lookahead 8 |
| work gates | `1984 / 1984` |
| termination | `completed` |
| runtime | about 51 minutes |
| peak bond | `605` |
| peak MPO elements | `1,627,736` |
| peak RSS | `7.5 GiB` |
| bond-cap rows | `0` |

The run was P11-blind (`--expected-bitstring ""`) and skipped sampling. Therefore
this is a successful full computational traversal, not yet an independently
verified answer bitstring.

## Comparison

The 512-bond control reached 77 gates in its two-hour wall cap. The tighter
cutoff/high-bond run reached 64 gates in its cap. R3 at cutoff `2e-3` and bond
4096 reached 78 gates in a clean rerun. R4 at cutoff `5e-3` completed all 1,984
gates without using the 4096 ceiling.

The evidence supports the conclusion that the earlier failure was dominated by
cutoff/unswapping workload and routing behavior, rather than a tensor-size
limit at bond 4096.

## Verification limitation

The repository contains the P9 expected bitstring and P9 verification tooling,
but no canonical P11 expected bitstring or independent P11 verifier. A blind
sampling run is therefore useful for producing a candidate distribution and
checking output stability, but cannot by itself prove that the modal candidate
is the externally intended target.

## Blind sampling verification

A repeat R4 traversal with `--samples 1000` completed in the same OpenBLAS
environment and produced 1,000 valid 98-bit samples. The distribution was
effectively diffuse: every sampled string occurred once, giving a modal count
of `1 / 1000`. This is a successful sampling-path smoke test, but it does not
provide a defensible P11 candidate. The `5e-3` cutoff is therefore sufficient
for full traversal but insufficient for answer extraction without an additional
tighter-cutoff fidelity experiment.

A follow-up fidelity run at cutoff `4e-3` also completed all 1,984 gates safely,
with peak bond 742 and peak RSS below the watchdog limit. Its 1,000 samples were
again all distinct, with modal count `1 / 1000`. The two independent blind
sampling runs therefore agree on the operational conclusion: the current MPO
approximation can traverse P11, but it does not preserve enough probability
concentration to identify a candidate bitstring.

## Final disposition

The computational campaign is closed without claiming a P11 answer. The next
scientifically meaningful step requires either an independently supplied
verifier/target or a new approximation method with a demonstrated fidelity
criterion. More samples from the current diffuse distribution would not solve
that limitation.
