from __future__ import annotations

from compiler.local_synthesis import extract_dependency_blocks
from compiler.numerical_synthesis import synthesize_numerical
from structural.qasm_events import Event, parse_qasm


def test_dependency_extractor_ignores_disjoint_interleaving(tmp_path):
    qasm = """OPENQASM 2.0;
include \"qelib1.inc\";
qreg q[4];
cz q[0],q[1];
u(0.1,0.2,0.3) q[3];
cz q[1],q[2];
u(0.4,0.5,0.6) q[3];
"""
    path = tmp_path / "interleaved.qasm"
    path.write_text(qasm)
    blocks = extract_dependency_blocks(parse_qasm(path), 3, max_global_span=10)
    assert any(block.wires == (0, 1, 2) and block.old_two_qubit == 2 for block in blocks)


def test_dependency_extractor_rejects_external_boundary(tmp_path):
    qasm = """OPENQASM 2.0;
include \"qelib1.inc\";
qreg q[4];
cz q[0],q[1];
cz q[1],q[3];
cz q[1],q[2];
"""
    path = tmp_path / "boundary.qasm"
    path.write_text(qasm)
    blocks = extract_dependency_blocks(parse_qasm(path), 3, max_global_span=10)
    assert not any(block.start == 0 and block.stop == 3 and block.wires == (0, 1, 2) for block in blocks)


def test_numerical_fallback_recovers_known_one_entangler_target():
    event = Event(0, "cz", (0, 1), (), 0, 0, 1)
    result = synthesize_numerical(
        (event,), (0, 1), 2, ((0, 1),), restarts=2, seed=7, max_nfev=80, wall_clock_s=5.0
    )
    assert result.success
    assert result.new_two_qubit == 1
    assert result.infidelity <= 1e-10
