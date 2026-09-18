import numpy as np

from p12_recovery.peak.consensus import consensus
from p12_recovery.peak.geometry import interaction_geometry
from p12_recovery.peak.mps import best_first_map, iswap_matrix
from p12_recovery.peak.qasm import parse
from p12_recovery.peak.structure import mirror_probe, weighted_backbone
from p12_recovery.peak.synthetic import control_family, statevector_to_mps
from p12_recovery.peak.tno import method_metadata
from p12_recovery.peak.watchdog import WatchdogLimits, child_process_count, swap_used_bytes


def test_iswap_semantics():
    expected = np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]])
    assert np.allclose(iswap_matrix(), expected)


def test_custom_iswap_qasm_is_directly_supported():
    parsed = parse("results/expert_review_p5_p6_p8_20260828/inputs/P8_grid_888_iswap.qasm")
    assert parsed.n_qubits == 40
    assert "iswap" in parsed.custom_gates
    assert sum(g.name == "iswap" for g in parsed.gates) == 888


def test_best_first_map_certifies_small_mps():
    tensors = [np.array([[[1 / np.sqrt(2), 0], [0, 1 / np.sqrt(2)]]]), np.array([[[1.0], [0.0]], [[0.0], [0.1]]])]
    result = best_first_map(tensors)
    assert result.certified
    assert result.bitstring == "00"


def test_control_families_have_exact_top_and_tunable_peak():
    for name in ("P8", "P6", "P5"):
        control = control_family(name, n=8)
        assert control["exact_top1"] == control["planted_label_for_test_only"]
        assert control["peak_probability"] > 0.09


def test_exact_synthetic_controls_recover_exact_map():
    for name in ("P8", "P6", "P5"):
        control = control_family(name, n=8)
        result = best_first_map(statevector_to_mps(control["statevector"], 8))
        assert result.certified
        assert result.bitstring == control["exact_top1"]


def test_consensus_does_not_double_count_same_family():
    result = consensus([
        {"method_family": "mps", "candidate": "01"},
        {"method_family": "mps", "candidate": "01"},
        {"method_family": "tno", "candidate": "01"},
    ])
    assert result["ranked"] == [("01", 2)]
    assert result["status"] == "CROSS_METHOD_CONVERGED_CANDIDATE"


def test_manifest_hash_and_fields():
    from p12_recovery.peak.manifest import profile
    data = profile("results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm")
    assert len(data["sha256"]) == 64
    assert data["canonical_logical_bit_order"] == "q0_first"
    assert data["qubit_count"] == 62


def test_watchdog_defaults_are_hard_bounded():
    limits = WatchdogLimits()
    assert limits.rss_hard_bytes == 24 * 1024**3
    assert limits.swap_growth_bytes == 2 * 1024**3
    assert child_process_count(99999999) == 0
    assert swap_used_bytes() is None or swap_used_bytes() >= 0


def test_structure_and_geometry_probes_are_answer_blind():
    circuit = parse("results/expert_review_p5_p6_p8_20260828/inputs/P8_grid_888_iswap.qasm")
    geometry = interaction_geometry(circuit)
    mirror = mirror_probe(circuit)
    backbone = weighted_backbone(circuit)
    assert geometry["geometry_path_status"] == "DIAGNOSTIC_ONLY"
    assert mirror["answer_blind"] and backbone["answer_blind"]
    assert geometry["unique_edges"] == 63


def test_tno_metadata_forbids_joint_map_claim():
    assert method_metadata(max_bond=4, cutoff=1e-2)["joint_map_claim"] is False
