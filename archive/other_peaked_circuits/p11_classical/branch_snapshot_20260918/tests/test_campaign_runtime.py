from p12_recovery.peak.campaign_runtime import CampaignBudget


def test_budget_has_hard_deadline_and_start_guard():
    budget = CampaignBudget(100.0, 3600.0)
    assert budget.deadline == 3700.0
    assert budget.remaining(250.0) == 3450.0
    assert budget.can_start(250.0, 3000.0)
    assert not budget.can_start(250.0, 3501.0)


def test_cooldown_only_follows_long_stage():
    budget = CampaignBudget(0.0, 1000.0, cooldown_minutes=5)
    assert budget.cooldown_seconds(1800.0) == 0.0
    assert budget.cooldown_seconds(1800.1) == 300.0
