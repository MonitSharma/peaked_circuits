import numpy as np
from qiskit import QuantumCircuit

from p12_recovery.bluequbit.tno import contract_core, finish_state, iter_layers, product_marginal_bitstring


def test_tno_fixture_preserves_product_peak_and_completes():
    qc = QuantumCircuit.from_qasm_file("tests/fixtures/p1_u_cz.qasm")
    core, trace, aborted = contract_core(list(iter_layers(qc)), chunk_size=1, max_bond=4, cutoff=0.0, max_seconds=30.0)
    assert not aborted
    assert trace
    state = finish_state(core, max_bond=4, cutoff=0.0)
    bitstring, p0s = product_marginal_bitstring(state)
    assert bitstring == "00"
    assert np.all(np.asarray(p0s) >= 0.0)
    assert np.all(np.asarray(p0s) <= 1.0)
