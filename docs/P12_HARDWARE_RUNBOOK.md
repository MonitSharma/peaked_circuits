# P12 physical-campaign runbook

1. Run `./.venv/bin/python -m p12_recovery.cli hardware-preflight --batch batch_001 --shots 400`.
2. Review the JSON and confirm the exact target is `Helios-1`, the 98-qubit capacity, frozen source/QIR/bitcode hashes, syntax evidence, mapping evidence, and derived cap.
3. Run `hardware-submit --dry-run` and verify `provider_call_made=false`.
4. Only an explicitly authorized operator may set `P12_ENABLE_PHYSICAL_HELIOS=1`, pass `--execute-hardware`, provide `P12_CONFIRM_PAID_EXECUTION=I_UNDERSTAND_THIS_MAY_CONSUME_HQC`, and type the confirmation.
5. If a job is submitted, use `hardware-status` and then `hardware-retrieve --batch ...`; never recreate or resubmit a saved batch.
6. Normalize provider output with the frozen mapping, hash raw and canonical artifacts, analyze batches target-blind, and freeze the discovery candidate before any confirmation decision.

The emulator pilot remains a separate, opt-in workflow and is not part of this milestone.
