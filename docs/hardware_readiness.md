# Hardware readiness

State: **READY_FOR_FUTURE_HARDWARE_SUBMISSION_BUT_NOT_SUBMITTED**

P12 is prepared for a future explicitly authorized physical submission. No physical
hardware or emulator execution is authorized by this state.

- [x] source_hash_frozen
- [x] compiler_version_frozen
- [ ] backend_identified
- [ ] backend_has_98_qubits
- [ ] target_validity_passed
- [ ] compiled_circuit_hash_recorded
- [ ] logical_permutation_resolved
- [ ] measurement_mapping_complete
- [ ] mapping_validation_passed
- [x] synthetic_tests_passed
- [x] fixture_semantic_tests_passed
- [x] cost_estimate_obtained
- [x] shot_protocol_frozen
- [ ] recovery_method_frozen
- [ ] tracker_protocol_confirmed
- [x] repository_commit_recorded
- [ ] repository_commit_tagged
- [x] hardware_guard_tests_passed
- [x] qir_export_completed
- [x] qir_hash_recorded
- [x] qir_structural_validation_passed
- [x] logical_to_qir_mapping_complete
- [x] mapping_case_qir_exports_passed
- [x] mapping_case_syntax_checks_passed
- [x] p12_syntax_check_passed
- [x] p12_submitted_bitcode_hash_matches
- [x] p12_target_is_helios_1sc
- [x] provider_result_order_verified
- [x] emulator_mapping_validation_passed
- [x] ready_for_p12_emulator_pilot
- [ ] p12_emulator_pilot_complete

## Fresh provider evidence

- P12 syntax check: passed on `Helios-1SC`; job `92154b08-1e0a-4b82-a483-b6d59938b937`.
- Fresh costing API: `qnexus.qir.cost_confidence`, system `Helios-1`.
- Largest tested count within 3,000 HQC: 430 shots at 2,948 HQC.
- Recommended future batch: 400 shots with `max_cost=2742` HQC and 258 HQC headroom.
- Physical hardware jobs submitted in this goal: 0.
- Emulator jobs submitted in this goal: 0.
- Physical HQCs spent in this goal: 0.

Milestone 4 stops before physical hardware execution. Syntax acceptance, emulator mapping validation, and recovery accuracy are distinct evidence levels.
