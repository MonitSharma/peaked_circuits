from qiskit import QuantumCircuit
import quimb.tensor as qtn
from qiskit_quimb import quimb_circuit


def test_public_distillation_mapping_on_fixture():
    qc = QuantumCircuit.from_qasm_file("tests/fixtures/p1_u_cz.qasm")
    circuit = quimb_circuit(qc, quimb_circuit_class=qtn.CircuitPermMPS, max_bond=8, cutoff=0.0, progbar=False)
    mapping = [circuit.qubits.index(q) for q in range(circuit.N)]
    mapping = [mapping[q] for q in mapping]
    samples = ["".join(sample[q] for q in mapping) for sample in circuit.sample(10, seed=1234)]
    assert samples == ["00"] * 10
