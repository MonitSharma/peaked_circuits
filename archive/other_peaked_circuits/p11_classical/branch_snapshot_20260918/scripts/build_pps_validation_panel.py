"""Build tiny Qiskit reference circuits and dense |0> expectations for PPS validation."""
import json
from pathlib import Path
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_pp_gate_stream import canonical_stream

out = Path("julia/pps/validation")
out.mkdir(parents=True, exist_ok=True)
cases = []

def add(name, qc, q):
    # Qiskit Pauli labels are big-endian; construct the operator directly by index.
    label = ["I"] * qc.num_qubits
    label[qc.num_qubits - 1 - q] = "Z"
    expected = float(Statevector.from_instruction(qc).expectation_value(SparsePauliOp("".join(label))).real)
    payload = {"schema": "pps_validation_v1", "name": name, "num_qubits": qc.num_qubits,
               "observable_qiskit_zero_based": q, "expected": expected,
               "gates": canonical_stream(qc)}
    path = out / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    cases.append(str(path))

qc = QuantumCircuit(1); qc.h(0); add("h_z", qc, 0)
qc = QuantumCircuit(1); qc.rx(0.37, 0); add("rx_z", qc, 0)
qc = QuantumCircuit(1); qc.u(0.21, -0.48, 0.73, 0); add("u_z", qc, 0)
qc = QuantumCircuit(2); qc.h(0); qc.rzz(-0.63, 0, 1); qc.sx(1); add("rzz_two", qc, 0)
qc = QuantumCircuit(2); qc.cx(0, 1); qc.rz(0.41, 0); qc.x(1); add("cx_rz_x", qc, 1)
qc = QuantumCircuit(2); qc.cz(0, 1); qc.h(0); add("cz_two", qc, 1)
qc = QuantumCircuit(3); qc.u(0.21, -0.48, 0.73, 2); add("u_nonadjacent", qc, 2)
qc = QuantumCircuit(3); qc.h(0); qc.rzz(-0.63, 0, 2); add("rzz_nonadjacent", qc, 0)
qc = QuantumCircuit(2)
qc.unitary([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], [0, 1])
add("generic_two", qc, 0)

# Measurement order is checked independently because measurements are not propagated.
mqc = QuantumCircuit(2, 2)
mqc.measure(1, 0)
mqc.measure(0, 1)
measurement_order = [{"clbit": mqc.find_bit(bit).index, "qubit": mqc.find_bit(item.qubits[0]).index}
                     for item in mqc.data if item.operation.name == "measure" for bit in item.clbits]
(out / "measurement_order.json").write_text(json.dumps({"measurement_order_qiskit": measurement_order}, indent=2) + "\n")
assert measurement_order == [{"clbit": 0, "qubit": 1}, {"clbit": 1, "qubit": 0}]
print(json.dumps({"cases": cases}, indent=2))
