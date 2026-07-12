import pytest

from p12_recovery.constants import HARDWARE_CONFIRMATION
from p12_recovery.hardware_guard import (
    HardwareSubmissionBlocked,
    assert_hardware_submission_allowed,
)


def call(**overrides: object) -> str:
    values = {
        "execute_hardware": True,
        "environment": {
            "P12_ENABLE_HARDWARE": "1",
            "P12_CONFIRM_PAID_EXECUTION": HARDWARE_CONFIRMATION,
        },
        "readiness_passed": True,
        "device_is_physical": False,
        "backend_mode": "execute",
        "interactive_confirmed": True,
    }
    values.update(overrides)
    with pytest.raises(HardwareSubmissionBlocked) as exc:
        assert_hardware_submission_allowed(**values)  # type: ignore[arg-type]
    return str(exc.value)


def test_every_required_blocking_condition() -> None:
    assert "CLI flag" in call(execute_hardware=False)
    assert "P12_ENABLE_HARDWARE" in call(environment={})
    assert "P12_ENABLE_HARDWARE" in call(environment={"P12_ENABLE_HARDWARE": "0"})
    assert "required phrase" in call(environment={"P12_ENABLE_HARDWARE": "1"})
    assert "required phrase" in call(
        environment={"P12_ENABLE_HARDWARE": "1", "P12_CONFIRM_PAID_EXECUTION": "wrong"}
    )
    assert "readiness" in call(readiness_passed=False)
    assert "compile-only" in call(device_is_physical=True, backend_mode="compile_only")
    assert "interactive" in call(interactive_confirmed=False)
    assert "no functioning" in call()  # default tests can never submit either
