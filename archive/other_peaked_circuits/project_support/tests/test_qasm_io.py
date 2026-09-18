from pathlib import Path

import numpy as np

from p12_recovery.hashing import sha256_file
from p12_recovery.qasm_io import export_pytket_qasm, load_qasm, structural_signature


def test_parse_measurements_and_preserve(root: Path) -> None:
    source = root / "circuits/fixtures/bell.qasm"
    before = sha256_file(source)
    parsed = load_qasm(source)
    assert parsed.number_of_qubits == 2
    assert sum(op.name == "measure" for op in parsed.operations) == 2
    assert sha256_file(source) == before


def test_round_trip_structure(root: Path, tmp_path: Path) -> None:
    source = load_qasm(root / "circuits/fixtures/small_random.qasm")
    output = tmp_path / "roundtrip.qasm"
    export_pytket_qasm(source, output)
    reparsed = load_qasm(output)
    assert structural_signature(source) == structural_signature(reparsed)
    before = source.sdk_circuit.get_statevector()
    after = reparsed.sdk_circuit.get_statevector()
    phase = np.vdot(before, after)
    assert np.allclose(before, after * np.exp(-1j * np.angle(phase)))
