import json
import sys
from pathlib import Path
from qiskit import QuantumCircuit
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_pp_gate_stream import canonical_stream

qc = QuantumCircuit(2, 2)
qc.measure(1, 0)
qc.measure(0, 1)
expected = [{"clbit": 0, "qubit": 1}, {"clbit": 1, "qubit": 0}]
actual = [{"clbit": qc.find_bit(bit).index, "qubit": qc.find_bit(item.qubits[0]).index}
          for item in qc.data if item.operation.name == "measure" for bit in item.clbits]
assert actual == expected, (actual, expected)
assert canonical_stream(qc) == []
print(json.dumps({"status": "PASS", "measurement_order_qiskit": actual}))
