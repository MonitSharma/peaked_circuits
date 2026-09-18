"""Small, deterministic policy helpers for resumable night campaigns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignBudget:
    """Wall-clock budget shared by all stages in one controller invocation."""

    started_monotonic: float
    budget_seconds: float
    cooldown_minutes: float = 5.0
    cooldown_after_seconds: float = 30.0 * 60.0

    @property
    def deadline(self) -> float:
        return self.started_monotonic + self.budget_seconds

    def remaining(self, now: float) -> float:
        return max(0.0, self.deadline - now)

    def can_start(self, now: float, required_seconds: float = 0.0) -> bool:
        return self.remaining(now) >= max(0.0, required_seconds)

    def cooldown_seconds(self, elapsed_stage_seconds: float) -> float:
        if elapsed_stage_seconds > self.cooldown_after_seconds:
            return max(0.0, self.cooldown_minutes * 60.0)
        return 0.0
