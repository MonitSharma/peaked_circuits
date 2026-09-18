from p12_recovery.models import ReadinessState
from p12_recovery.readiness import readiness_state_from_checks


def test_local_export_alone_does_not_imply_syntax_readiness() -> None:
    state = readiness_state_from_checks(
        {"qir_export_completed": True, "qir_hash_recorded": True}, offline=True
    )
    assert state == ReadinessState.READY_FOR_QIR_EXPORT


def test_complete_local_qir_evidence_reaches_syntax_check_state() -> None:
    state = readiness_state_from_checks(
        {
            "qir_export_completed": True,
            "qir_hash_recorded": True,
            "qir_structural_validation_passed": True,
            "logical_to_qir_mapping_complete": True,
            "mapping_case_qir_exports_passed": True,
            "mapping_case_syntax_checks_passed": False,
            "p12_syntax_check_passed": False,
        },
        offline=True,
    )
    assert state == ReadinessState.READY_FOR_SYNTAX_CHECK


def test_syntax_success_only_reaches_emulator_mapping_validation() -> None:
    state = readiness_state_from_checks(
        {
            "mapping_case_syntax_checks_passed": True,
            "p12_syntax_check_passed": True,
            "provider_result_order_verified": False,
            "emulator_mapping_validation_passed": False,
        },
        offline=True,
    )
    assert state == ReadinessState.READY_FOR_EMULATOR_MAPPING_VALIDATION
    assert "READY_FOR_HARDWARE_SMOKE_TEST" not in {item.value for item in ReadinessState}
