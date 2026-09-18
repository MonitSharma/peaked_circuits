from __future__ import annotations

from dataclasses import dataclass

from p12_recovery.real_mpo_beam import RealMPOBeamEvaluator


@dataclass(frozen=True)
class FakeMPO:
    value: int
    sites: tuple[int, ...] = (0, 1, 2)


class FakeBackend:
    def apply_swaps(self, mpo, swaps, *, max_bond, cutoff):
        return FakeMPO(mpo.value + len(swaps))

    def apply_work(self, mpo, layer, *, max_bond, cutoff):
        return FakeMPO(mpo.value + layer)

    def metrics(self, mpo):
        return {"tensor_elements": float(mpo.value), "max_bond": float(mpo.value)}


def test_real_mpo_probe_isolated_and_commit_is_deterministic(tmp_path):
    evaluator = RealMPOBeamEvaluator(FakeBackend(), max_bond=16, cutoff=1e-4)
    parent = evaluator.snapshot_state(FakeMPO(0), permutation=(0, 1, 2))
    first = evaluator.evaluate_schedule(parent, ((0, 1),), work_layers=(2,), routing_debt=3)
    second = evaluator.evaluate_schedule(parent, ((1, 2),), work_layers=(1,), routing_debt=2)
    assert parent.mpo.value == 0
    committed, winner = evaluator.choose_and_commit(parent, (first, second))
    assert committed.mpo.value == 2
    assert winner.swaps == ((1, 2),)
    checkpoint = tmp_path / "snapshot.pkl"
    evaluator.checkpoint(committed, checkpoint)
    assert evaluator.restore(checkpoint).mpo.value == 2


def test_real_mpo_failure_is_reported_without_parent_mutation():
    class Failing(FakeBackend):
        def apply_swaps(self, mpo, swaps, *, max_bond, cutoff):
            raise MemoryError("synthetic overflow")

    evaluator = RealMPOBeamEvaluator(Failing(), max_bond=16, cutoff=1e-4)
    parent = evaluator.snapshot_state(FakeMPO(0), permutation=(0, 1, 2))
    result = evaluator.evaluate_schedule(parent, ((0, 1),))
    assert result.failure == "MemoryError: synthetic overflow"
    assert parent.mpo.value == 0
