import numpy as np

from p12_recovery.peak.iswap_frame import (
    lower_iswap_frame,
    physical_bitstring_to_logical,
    write_frame_qasm,
)
from p12_recovery.peak.qasm import Gate, PeakQASM, parse

S = np.diag([1.0, 1.0j]).astype(np.complex128)
H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
CZ = np.diag([1, 1, 1, -1]).astype(np.complex128)
ISWAP = np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]], dtype=np.complex128)


def _u(theta: float, phi: float, lam: float) -> np.ndarray:
    return np.array(
        [[np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
         [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)]],
        dtype=np.complex128,
    )


def _apply(state: np.ndarray, matrix: np.ndarray, qubits: tuple[int, ...], n: int) -> np.ndarray:
    tensor = state.reshape((2,) * n)
    order = list(qubits) + [q for q in range(n) if q not in qubits]
    moved = np.transpose(tensor, order).reshape(matrix.shape[0], -1)
    moved = matrix @ moved
    return np.transpose(moved.reshape((2,) * n), np.argsort(order)).reshape(-1)


def _matrix(gate: Gate) -> np.ndarray:
    if gate.name == "u":
        return _u(*gate.params)
    return {"s": S, "h": H, "cz": CZ, "iswap": ISWAP}[gate.name]


def _simulate(circuit: PeakQASM) -> np.ndarray:
    state = np.zeros(2 ** circuit.n_qubits, dtype=np.complex128)
    state[0] = 1.0
    for gate in circuit.gates:
        state = _apply(state, _matrix(gate), gate.qubits, circuit.n_qubits)
    return state


def _physical_to_logical_state(state: np.ndarray, logical_to_site: tuple[int, ...]) -> np.ndarray:
    n = len(logical_to_site)
    tensor = state.reshape((2,) * n)
    # logical axis q receives the physical axis logical_to_site[q].
    return np.transpose(tensor, logical_to_site).reshape(-1)


def test_iswap_identity() -> None:
    assert np.allclose(ISWAP, np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]]))
    assert np.allclose(ISWAP, np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) @ CZ @ np.kron(S, S))


def test_frame_matches_native_circuit_on_random_small_circuits() -> None:
    rng = np.random.default_rng(18)
    for n in (2, 3, 4, 6, 10):
        gates: list[Gate] = []
        for _index in range(2 * n + 7):
            q = int(rng.integers(n))
            gates.append(Gate("u", (q,), tuple(float(v) for v in rng.normal(size=3))))
            a, b = rng.choice(n, size=2, replace=False)
            gates.append(Gate("iswap", (int(a), int(b))))
        circuit = PeakQASM(n, tuple(gates), ("iswap",))
        frame = lower_iswap_frame(circuit)
        expected = _simulate(circuit)
        actual = _physical_to_logical_state(_simulate(frame.as_peak_qasm()), frame.logical_to_site)
        assert np.allclose(actual, expected, atol=1e-12)
        assert sorted(frame.logical_to_site) == list(range(n))
        assert sorted(frame.site_to_logical) == list(range(n))


def test_p8_frame_has_no_two_qubit_iswap_or_swap() -> None:
    circuit = parse("results/expert_review_p5_p6_p8_20260828/inputs/P8_grid_888_iswap.qasm")
    frame = lower_iswap_frame(circuit)
    assert frame.iswap_count == 888
    assert len(frame.gates) == len(circuit.gates) + 2 * frame.iswap_count
    assert not any(gate.name in {"iswap", "swap"} for gate in frame.gates)
    assert sum(gate.name == "cz" for gate in frame.gates) == 888
    assert sum(gate.name == "s" for gate in frame.gates) == 1776


def test_p8_frame_qasm_round_trip_has_expected_shape(tmp_path) -> None:
    circuit = parse("results/expert_review_p5_p6_p8_20260828/inputs/P8_grid_888_iswap.qasm")
    frame = lower_iswap_frame(circuit)
    output = tmp_path / "p8_frame.qasm"
    write_frame_qasm(frame, output)
    round_trip = parse(output)
    assert len(round_trip.gates) == 4480
    assert sum(gate.name == "cz" for gate in round_trip.gates) == 888
    assert sum(gate.name == "s" for gate in round_trip.gates) == 1776


def test_mapping_and_qasm_writer(tmp_path) -> None:
    circuit = PeakQASM(2, (Gate("iswap", (0, 1)), Gate("u", (0,), (0.1, 0.2, 0.3))), ("iswap",))
    frame = lower_iswap_frame(circuit)
    assert frame.logical_to_site == (1, 0)
    assert physical_bitstring_to_logical("01", frame.logical_to_site) == "10"
    output = tmp_path / "frame.qasm"
    write_frame_qasm(frame, output)
    lowered = parse(output)
    assert all(gate.name != "iswap" for gate in lowered.gates)
    assert len(lowered.gates) == 4
