from p12_recovery.peak.ordering import compare_orderings, weighted_routing_proxy
from p12_recovery.peak.qasm import parse


def test_weighted_ordering_metrics_are_reproducible() -> None:
    circuit = parse("results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm")
    result = compare_orderings(circuit)
    assert result["answer_blind"] is True
    assert set(result["orders"]) >= {"identity", "spectral", "heavy_greedy", "rcm"}
    for order in result["orders"].values():
        assert sorted(order) == list(range(62))
    assert result["metrics"]["identity"]["weighted_bandwidth"] >= 0


def test_routing_proxy_rejects_incomplete_order() -> None:
    circuit = parse("circuits/fixtures/small_random.qasm")
    try:
        weighted_routing_proxy(circuit, [0, 1])
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete order was accepted")
