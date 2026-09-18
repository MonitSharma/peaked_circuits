# P6 native-ZZPhase Helios-1SC syntax check

The optimized P6 QIR was submitted to **Helios-1SC only**, without rebasing
the native `ZZPhase` gates to CZ. The syntax-check job completed successfully.

## Result

- Target: `Helios-1SC` (`syntax_checker`)
- Job ID: `06215946-2e5f-488b-8414-57b4fc4a7266`
- Final status: `COMPLETED`
- Qubits: 62
- Measurements: 62
- Native `ZZPhase` gates: 2,798
- CZ gates: 0
- `Rz` gates: 29,536
- `Rx` gates: 16,242
- Reported HQC charge: none

This confirms that the native-ZZPhase QIR artifact is accepted by the
Helios-1SC syntax-check path. It does not execute shots, simulate the circuit,
or provide a shot-scaled HQC cost ladder.

## Artifacts

- Native QIR: `results/hardware/p6_optimized_compile_20260907/p6_native_zzphase.qir.ll`
- Native bitcode: `results/hardware/p6_optimized_compile_20260907/p6_native_zzphase.qir.bc`
- Machine-readable report: `results/hardware/p6_optimized_compile_20260907/native_zzphase_syntax_report.json`

Hashes are recorded in the machine-readable report. No emulator or physical
Helios-1 execution was submitted.
