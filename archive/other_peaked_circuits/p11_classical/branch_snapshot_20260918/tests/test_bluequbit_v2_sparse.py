from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from p12_recovery.bluequbit.profile import _u_matrix
from p12_recovery.bluequbit.sparse_sv import SparseState, _rss_bytes, dependency_schedule
from structural.qasm_events import parse_qasm


def test_specialized_cz_preserves_support_and_matches_phase():
    state = SparseState(2, basis=np.arange(4), alpha=np.array([1, 2, 3, 4], dtype=np.complex128))
    before = state.basis.copy()
    state.evolve_cz(0, 1)
    assert np.array_equal(before, state.basis)
    assert np.allclose(state.alpha, [1, 2, 3, -4])


def test_specialized_iswap_preserves_support_and_matches_dense_action():
    state = SparseState(2, basis=np.arange(4), alpha=np.array([1, 2, 3, 4], dtype=np.complex128))
    before = state.basis.copy()
    state.evolve_iswap(0, 1)
    expected = np.array([1, 3j, 2j, 4], dtype=np.complex128)
    assert np.array_equal(np.sort(before), np.sort(state.basis))
    actual = np.zeros(4, dtype=np.complex128)
    actual[state.basis] = state.alpha
    assert np.allclose(actual, expected)


def test_specialized_u_matches_dense_update_on_fixture_state():
    state = SparseState(2, basis=np.arange(4), alpha=np.array([1, 2, 3, 4], dtype=np.complex128))
    matrix = _u_matrix(0.3, 0.2, -0.4)
    dense = np.zeros(4, dtype=complex)
    dense[:] = state.alpha
    state.evolve_u(matrix, 0)
    expected = np.zeros(4, dtype=complex)
    for basis in range(4):
        bit = (basis >> 0) & 1
        for out_bit in (0, 1):
            out = (basis & ~1) | out_bit
            expected[out] += matrix[out_bit, bit] * dense[basis]
    assert np.allclose(state.alpha[np.argsort(state.basis)], expected[np.sort(state.basis)])


def test_truncation_records_pre_renormalization_mass():
    state = SparseState(2, basis=np.arange(4), alpha=np.array([3, 1, 0, 0], dtype=np.complex128))
    result = state.truncate(1)
    assert result["support_before"] == 4
    assert result["support_after"] == 1
    assert result["discarded_mass"] > 0
    assert abs(state.norm - 1.0) < 1e-12


def test_probability_fraction_truncation_records_tail_mass():
    state = SparseState(2, basis=np.arange(4), alpha=np.array([3, 1, 0, 0], dtype=np.complex128))
    result = state.truncate(0, 0.8)
    assert result["support_after"] == 1
    assert result["discarded_mass"] > 0


def test_rss_watchdog_reports_reasonable_mac_scale():
    assert _rss_bytes() < 2 * 1024**3


def test_cz_first_schedule_preserves_same_wire_order():
    events = parse_qasm("tests/fixtures/tiny.qasm").events
    scheduled = dependency_schedule(events, "cz_first")
    assert {e.index for e in scheduled} == {e.index for e in events}
    for q in range(2):
        assert [e.index for e in scheduled if q in e.wires] == [e.index for e in events if q in e.wires]


def test_p1_kernel_matches_external_qstvec_on_fixture():
    sys.path.insert(0, str(Path("external/qstvec/src").resolve()))
    from qstvec import Statevector as GenericStatevector

    state = SparseState(2)
    generic = GenericStatevector(2)
    matrix = _u_matrix(0.21, -0.48, 0.73)
    state.evolve_u(matrix, 0)
    generic.evolve(matrix, [0])
    state.evolve_cz(0, 1)
    generic.evolve(np.diag([1, 1, 1, -1]), [0, 1])
    assert np.array_equal(state.basis, generic.basis)
    assert np.allclose(state.alpha, generic.alpha)


def test_local_dense_kernel_matches_sequential_u_and_cz():
    from scripts.run_bluequbit_p1_sparse_blocks import embed_gate
    state_local = SparseState(2)
    state_seq = SparseState(2)
    u = _u_matrix(0.21, -0.48, 0.73)
    cz = np.diag([1, 1, 1, -1]).astype(complex)
    state_local.evolve_local(embed_gate(cz, (0, 1), [0, 1]) @ embed_gate(u, (0,), [0, 1]), [0, 1])
    state_seq.evolve_u(u, 0)
    state_seq.evolve_cz(0, 1)
    assert np.array_equal(state_local.basis, state_seq.basis)
    assert np.allclose(state_local.alpha, state_seq.alpha)
    assert abs(state_local.norm - state_seq.norm) < 1e-12


def test_alternate_ready_priority_is_still_topological():
    from scripts.run_bluequbit_p1_sparse_blocks import blocks_from_events
    events = parse_qasm("tests/fixtures/tiny.qasm").events
    blocks = blocks_from_events(events, 2, "u_first")
    flattened = [event.index for block in blocks for event in block]
    assert sorted(flattened) == [0, 1]
