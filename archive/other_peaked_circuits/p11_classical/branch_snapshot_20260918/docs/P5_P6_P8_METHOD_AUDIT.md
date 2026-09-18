# Method Audit

> **Updated 2026-08-31.** Use [P6_P8_REASSESSMENT_20260831.md](P6_P8_REASSESSMENT_20260831.md)
> as the current status source. Older rows are retained as method-family
> provenance and are no longer live recommendations.

| Family | Status | Scope |
|---|---|---|
| Structural profiling/manifests | tested/promising | P5, P6, P8; hashes and graph statistics |
| Direct iSWAP semantics | tested/promising | parser and exact 4x4 fixture |
| Best-first MPS MAP | tested/promising | exact bound on normalized right-canonical MPS |
| Generic/permutation MPS ladders | tested; fidelity-gate rejected | P8 D128/D256 and P6 D64/D128 (including annealed ordering) fail retained-fidelity or stability checks; no promoted candidate |
| Geometry-aware P8 | tested/closed at bounded probe | native-graph PEPS D4/md2 → D4/md3 changed diagnostics; classified `GEOMETRY_UNSTABLE`, D8 withheld |
| Mirror/MPO/TNO | structural gate tested; generic TNO fixture tested | P6/P5 mirror probes weak; Bell TNO completes; target MPO prefix and calibrated P6 full run complete as diagnostics only |
| MPO/unswapping target path | locally validated, not a recovery | Read-only local solver checkout passes the P9/P5 calibration. P6 D512 completes only at flat, loose settings; P8's historical late controller reaches 804/808 but clean tail attempts do not reach sampling. No target answer is asserted. |
| P6/P8 structural reconstruction | tested; local signal only | P8 unitary and graph/mirror scans and P6 patch/fingerprint scans found local coincidences but no stable global permutation |
| Runtime safety | fixed and verified | Matplotlib is forced to `Agg`; launcher creates a writable Numba cache; full tests pass (202 passed, one warning) |
| Hardware/cloud methods | prohibited | never part of this campaign |
