import numpy as np

from p12_recovery.peak.qasm import parse
from p12_recovery.peak.ttn import build_unweighted_tree, build_weighted_tree, cut_rank_profile, exact_tree_topk, tree_leaves
from p12_recovery.peak.ttn_state import simulate_ttn
from p12_recovery.peak.qasm import Gate, PeakQASM


def test_weighted_tree_covers_each_p8_qubit_once() -> None:
    circuit = parse("results/expert_review_p5_p6_p8_20260828/inputs/P8_grid_888_iswap.qasm")
    tree = build_weighted_tree(circuit)
    leaves = tree_leaves(tree)
    assert len(leaves) == 40
    assert sorted(leaves) == list(range(40))
    assert tree.children and tree.cut_weight >= 0
    unweighted = build_unweighted_tree(circuit)
    assert sorted(tree_leaves(unweighted)) == list(range(40))


def test_exact_tree_control_reports_cut_ranks_and_peak() -> None:
    rng = np.random.default_rng(4)
    state = rng.normal(size=2**3) + 1j * rng.normal(size=2**3)
    state /= np.linalg.norm(state)
    circuit = parse("circuits/fixtures/small_random.qasm")
    tree = build_weighted_tree(circuit)
    profile = cut_rank_profile(state, tree)
    assert profile and all(row["rank"] >= 1 for row in profile)
    top = exact_tree_topk(state, k=3)
    assert len(top) == 3 and top[0]["probability"] >= top[-1]["probability"]


def test_target_ttn_two_qubit_control_preserves_exact_probability_mass() -> None:
    circuit = PeakQASM(2, (Gate("h", (0,)), Gate("cx", (0, 1))), ())
    state = simulate_ttn(circuit, max_bond=4, cutoff=0.0)
    state.apply_one_qubit(0, np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    state.apply_two_qubit(0, 1, np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]))
    assert np.isclose(state.mass({}), 1.0, atol=1e-10)
    assert np.isclose(state.mass({0: 0, 1: 0}), 0.5, atol=1e-10)
    assert np.isclose(state.mass({0: 1, 1: 1}), 0.5, atol=1e-10)
    assert np.isclose(state.mass({0: 0, 1: 1}), 0.0, atol=1e-10)


def test_ttn_marginal_factors_are_positive_on_exact_control() -> None:
    circuit = PeakQASM(2, (Gate("h", (0,)), Gate("cx", (0, 1))), ())
    state = simulate_ttn(circuit, max_bond=4, cutoff=0.0)
    state.apply_one_qubit(0, np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    state.apply_two_qubit(0, 1, np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]))
    unary, pairwise, total = state.marginal_factors([(0, 1)])
    assert np.isclose(total, 1.0, atol=1e-10)
    assert np.all(unary >= 0) and np.all(pairwise[(0, 1)] >= 0)
    assert np.isclose(pairwise[(0, 1)].sum(), 1.0, atol=1e-10)
