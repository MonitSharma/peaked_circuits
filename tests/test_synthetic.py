import numpy as np

from p12_recovery.synthetic import (
    aggregate_shots,
    asymmetric_readout_shots,
    correlated_burst_shots,
    independent_bit_flip_shots,
    mixture_shots,
)


def test_independent_shot_count_rate_and_seed() -> None:
    target = "0" * 98
    first = independent_bit_flip_shots(target, 1000, error_probability=0.1, seed=9)
    second = independent_bit_flip_shots(target, 1000, error_probability=0.1, seed=9)
    assert first == second and len(first) == 1000
    rate = sum(value.count("1") for value in first) / (1000 * 98)
    assert abs(rate - 0.1) < 0.01
    assert sum(aggregate_shots(first).values()) == 1000


def test_asymmetric_burst_and_mixture_behavior() -> None:
    asymmetric = asymmetric_readout_shots(
        "1" * 50 + "0" * 50, 2000, p_1_to_0=0.2, p_0_to_1=0.05, seed=2
    )
    matrix = np.array([[int(x) for x in row] for row in asymmetric])
    assert matrix[:, :50].mean() < 0.85
    assert matrix[:, 50:].mean() < 0.08
    burst = correlated_burst_shots("0000", 50, groups=[[1, 2]], burst_probability=1, seed=1)
    assert set(burst) == {"0110"}
    mixture = mixture_shots(
        "0000",
        500,
        target_weight=0.7,
        secondary_weight=0.2,
        uniform_weight=0.1,
        cluster_error_probability=0,
        seed=5,
    )
    assert len(mixture) == 500
    assert mixture.count("0000") > mixture.count("1111")
