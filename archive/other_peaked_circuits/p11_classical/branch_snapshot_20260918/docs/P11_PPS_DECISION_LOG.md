# PPS decision log

| Phase | Result | Decision |
|---|---|---|
| Julia/package staging | PASS | Julia 1.10.10 and the pinned PauliPropagation commit loaded successfully. |
| Dense adapter validation | PASS | Five independent Qiskit cases passed at `<=2.22e-16` error. |
| P9 smoke, threshold `1e-3` | COMPUTED but scientifically unusable | All 8 fixed observables returned zero terms and zero expectation; no convergence claim. |
| P9 convergence probe, threshold `1e-4` | FAIL / aborted | The representative position-1 run produced no output after about 125 seconds and showed multi-GiB resident-memory growth while consuming CPU. |
| P11 | NOT RUN | Strict P9 GO was not established; blindness remains intact. |
| Thread scaling | PASS / bounded only | Fixed 200-gate P9 prefix was deterministic at 1/4/8/18 threads; 8 threads was marginally fastest internally. |
| Existing Python health | PASS | 146 non-hardware tests passed in 61.15 seconds. |

Final state: `NO_GO_PPS_P9_SMOKE`.

This is not evidence that P11 is mathematically impossible. It is evidence that this unmodified PPS representation and threshold ladder did not establish a trustworthy P9 result on the current CPU run, so proceeding to P11 would violate the control-gated protocol.
