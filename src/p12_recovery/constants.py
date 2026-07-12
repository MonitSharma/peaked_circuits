from pathlib import Path

SCHEMA_VERSION = "1.0"
CIRCUIT_ID = "peaked_circuit_P12_Hqap_98x2457"
P12_QUBITS = 98
CANONICAL_BIT_ORDER = "logical_q0_to_q97_left_to_right"
CANONICAL_DESCRIPTION = (
    "Character position i corresponds to logical qubit q[i], with q[0] on the left."
)
TRACKER_REPOSITORY = (
    "https://github.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io"
)
TRACKER_API = (
    "https://api.github.com/repos/quantum-advantage-tracker/quantum-advantage-tracker.github.io"
)
REGISTRY_PATH = "data/classically-verifiable-problems/circuit-models.json"
DEFAULT_QASM = Path("circuits/original") / f"{CIRCUIT_ID}.qasm"
HARDWARE_CONFIRMATION = "I_UNDERSTAND_THIS_MAY_CONSUME_HQC"
