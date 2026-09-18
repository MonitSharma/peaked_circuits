# P11 method-exhaustion audit

The campaign was run on `p11_classical`, HEAD `e54653e`, with P9 SHA256
`cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35` and P11
SHA256 `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`.

| Requirement | Evidence | Audit result |
|---|---|---|
| Toolchain installation | `INSTALLATION_LOG.md`, `toolchain_smoke.json` | all six requested packages imported; all smoke tests passed |
| Dependency-aware patches | `compiler/local_synthesis.py`, extractor tests, frozen panel | verified causal-boundary behavior; 60 patches frozen |
| q=3/q=4 exact synthesis | `synthesis_panel_results.csv` | BQSKit ran q=3 and q=4; bounded timeouts captured; two exact reductions |
| Numerical fallback | `compiler/numerical_synthesis.py`, panel CSV | all panel blocks received bounded numerical attempts and permutation ledger |
| Approximate tolerances | `synthesis_panel_summary.json` | exactly 1e-8, 1e-6, 1e-4 evaluated; no global rewrite accepted |
| PyZX | `pyzx_results.json`, reduced QASM | exact graph rewrite completed; below effective global gate |
| QCEC | `qcec_results.json`, smoke JSON | local verification passed; whole P9 bounded timeout |
| DDSIM | `ddsim_results.json` | P9 first prefix timed out; P11 not attempted |
| CircuitPermMPS | `circuitpermmps_results.json` | P9 full pilot completed; no concentration/56-of-56 peak |
| Beam controller | `beam_controller_results.json` | bounded projected beam ran; production schedule injection technically absent |
| Blindness | `RUN_STATE.json`, no candidate artifact | P11 not processed; contamination false |
| Reproducibility | `SHA256SUMS`, environment and logs | required checksums and environment recorded |

The negative recommendation is bounded to the tested machine, toolchain,
algorithms, budgets, and P9 calibration gates. It does not claim that P11 is
classically impossible.

## Method-family inventory

The following inventory records the practical method families considered for
peaked circuits, the public implementation or line of work used as the
reference point, and the current P11 assessment. “Closed” means closed under
the implementation, budgets, and calibration gates actually tested here; it is
not a claim of computational impossibility. The remaining bold families are
the only materially different or inexpensive follow-ups currently worth
considering.

| Family | Public implementation / work | Status in this project | P11 assessment |
|---|---|---|---|
| MPS | Aer, quimb, Enigma solvers, others | Extensively tested | Closed |
| MPO + unswapping | Kremer–Dupuis | Extensively tested | Closed under current method |
| Marginal distillation | Kremer–Dupuis / HQAP attacks | Tested | Closed |
| Beam/MAP decoding | Enigma-style methods and project decoder | Tested | Closed |
| Sparse statevector | qstvec | Tested | Closed |
| Adaptive sparse basis | BASS | Tested | Closed under published implementation |
| Decision diagrams | DDSIM-type methods | Largely investigated | Very low priority |
| Generic TN contraction | quimb/cotengra/HPC | Investigated | Low priority |
| Official TNO contraction | Official peaked-circuit implementation | Not tested in this project | **Open** |
| Official distillation | Official peaked-circuit implementation | Not tested in this project; distinct from low-bond MPS distillation | **Open** |
| **Pauli propagation** | Modern PPS libraries | Not deeply calibrated here | **Possible bounded test** |
| **Sparse tensor networks** | Miller et al. 2026 | Not tested | **Genuinely different** |
| **2D loopy TN/BP** | TNQS.jl | Not directly tested in current form | Conditional |
| **Magic-depth decomposition** | Zhang & Zhang | Not structurally audited | **Cheap diagnostic** |

This table is the scope boundary for the exhaustion claim. In particular,
Pauli propagation, sparse tensor networks, 2D loopy tensor-network/belief
propagation, and magic-depth decomposition should not be described as tested
and closed. If the campaign is reopened, the order of operations should be:
first a cheap magic-depth structural diagnostic, then a bounded Pauli-
propagation feasibility test, followed by sparse-TN work only if it passes a
small-instance/P9 control gate. The conditional 2D loopy-TN route requires a
specific mapping or locality reduction before it is actionable.
