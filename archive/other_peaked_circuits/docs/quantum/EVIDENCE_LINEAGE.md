# Hardware evidence lineage

The lineage below uses the committed organized package. Hashes are retained
from historical manifests where available; hashes shown for copied artifacts
are hashes of byte-identical copies.

| Problem | Artifact | Path | SHA-256 | Parent/transformation | Validation |
|---|---|---|---|---|---|
| P11 | Source QASM | `results/quantinuum/p11/quantum/source/P11_hqap_1999.qasm` | `1373d50c...1b3372` | Upstream supplied QASM | Byte-preserved; source hash in run record |
| P11 | Submitted bitcode | `results/quantinuum/p11/quantum/submitted_input.bc` | `a25a9a74...1ab465` | Deterministic local QASM→QIR/bitcode | Matches provider manifest/checksum |
| P11 | Provider job | `results/quantinuum/p11/quantum/job.json` | — | Nexus job reference | `COMPLETED`; job ID retained |
| P11 | Raw result | `results/quantinuum/p11/quantum/raw_provider_result.json` | `1dc8ea57...c57be6` (provider payload) | Provider output | Preserved unchanged |
| P11 | Canonical shots | `results/quantinuum/p11/classical/raw/*.shots.jsonl` | `29d10fa9...9e768` (copy hash) | Raw 98-label chunking | 51 complete 98-bit records |
| P11 | Analysis | `results/quantinuum/p11/classical/analysis.json` | — | Canonical counts | Target-blind; descriptive pair counts |
| P12 | Source QASM | `results/quantinuum/p12/quantum/source/peaked_circuit_P12_Hqap_98x2457.qasm` | `868ff86a...be961d` | Repository byte-preserved source | Source hash retained |
| P12 | Submitted bitcode | `results/quantinuum/p12/quantum/submitted_input.bc` | `c6996dfb...e371d` (copy hash) | Deterministic local QASM→QIR/bitcode | Provider artifact retained |
| P12 | Provider job | `results/quantinuum/p12/quantum/job.json` | — | Nexus job reference | `COMPLETED`; job ID retained |
| P12 | Raw result | `results/quantinuum/p12/quantum/raw_result.json` | `c45634e6...5ac82` | Provider output | ASCII framing text; historical name preserved |
| P12 | Repaired framing | `results/quantinuum/p12/quantum/raw_result_framing_repaired.qir` | — | Structural framing repair | 205 diagnostic cycles |
| P12 | Canonical shots | `results/quantinuum/p12/classical/raw/reconstructed_200_shots.jsonl` | `cc31b30a...6bab07` | Exclude five overlap replicas | 200 canonical shots |
| P12 | Counts | `results/quantinuum/p12/classical/raw/reconstructed_counts.json` | `b28ba3f8...85ab1b` | Canonical shot aggregation | Manifest/checksum verified |
| P12 | Analysis | `results/quantinuum/p12/classical/analysis.json` | — | Canonical counts | Target-blind decoder comparison |

The abbreviated hashes above are for readability; complete values are in the
provider/reconstruction `SHA256SUMS` files and the JSON manifests. No external
verification result is used as an input to the target-blind analysis.
