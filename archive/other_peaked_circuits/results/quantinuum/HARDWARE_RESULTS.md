# Quantinuum hardware results

| Problem | Qubits | 2Q gates | Backend | Requested | Returned/reconstructed | HQC | Recovery | Verification |
|---|---:|---:|---|---:|---:|---:|---|---|
| P11 | 98 | 1,999 CZ | Helios-1 | 50 | 51 returned | 282.98 | Exploratory mode/cluster diagnostics | Later external answer reported; target-blind structure weak |
| P12 | 98 | 2,457 CZ | Helios-1 | 200 | 200 reconstructed from 205 diagnostic cycles | 1,373.4 | Most-frequent, weighted-medoid, cluster consensus agreed | Later external verification reported; no advantage claim |

Timing details, raw data, and analysis are linked from the per-problem pages.

## Cross-problem analysis audit (2026-09-07)

P11 and P12 were reanalysed locally from their retained canonical shot
records. No new provider jobs were submitted and no HQCs were spent. P11's
weighted medoid and cluster consensus recovered the externally accepted answer;
P12's most-frequent, weighted medoid, and cluster consensus did so as well.
Bitwise majority was one bit away for P11 and 13 bits away for P12.

This validates the retained recovery pipeline as a positive control. It does
not turn the recovery statistics into a quantum-advantage claim, and it does
not rescue P6, whose corrected five-batch dataset contains 500 unique strings
with no reproducible peak.

See `results/quantinuum/positive_control_audit_20260907/audit.md` for the
reproducible audit and `results/hardware/p6_five_batch_corrected_analysis_20260907/analysis.md`
for the corrected P6 result.
