from pathlib import Path

import pytest

from p12_recovery.backends.quantinuum import CompiledCircuitArtifact
from p12_recovery.bit_ordering import (
    build_measurement_mapping,
    canonical_to_raw_bitstring,
    raw_value_to_canonical,
)
from p12_recovery.compilation import trace_measurements
from p12_recovery.mapping_validation import (
    run_mapping_validation,
    validate_observed_case,
    validation_patterns,
)


def test_multiple_renamed_registers_and_noncontiguous_local_indices() -> None:
    layout = [
        {
            "name": "alpha",
            "classical_indices": [0, 1],
            "bit_indices": [2, 9],
        },
        {
            "name": "result_bits",
            "classical_indices": [2, 3, 4],
            "bit_indices": [1, 4, 8],
        },
    ]
    mapping = build_measurement_mapping(
        logical_to_classical={i: i for i in range(5)},
        sdk_string_order="msb_left",
        register_layout=layout,
    )
    canonical = "00101"
    raw = canonical_to_raw_bitstring(canonical, mapping)
    assert raw_value_to_canonical(raw, mapping) == canonical
    assert {entry.classical_register_name for entry in mapping.entries} == {
        "alpha",
        "result_bits",
    }


def test_extra_scratch_bits_are_excluded() -> None:
    mapping = build_measurement_mapping(
        logical_to_classical={i: i for i in range(2)},
        sdk_string_order="lsb_left",
        register_layout=[{"name": "out", "classical_indices": [0, 1, 2]}],
    )
    assert raw_value_to_canonical("101", mapping) == "10"


def test_unknown_mapping_and_leading_zero_failures() -> None:
    mapping = build_measurement_mapping(
        logical_to_classical={0: 0, 1: 1},
        sdk_string_order="lsb_left",
        register_layout=[{"name": "out", "classical_indices": [0, 1]}],
    )
    assert raw_value_to_canonical("01", mapping) == "01"
    with pytest.raises(ValueError, match="width"):
        raw_value_to_canonical("1", mapping)
    with pytest.raises(ValueError, match="incomplete"):
        raw_value_to_canonical("01", mapping.model_copy(update={"complete": False, "entries": []}))


def test_mapping_patterns_expose_reversal_and_register_order() -> None:
    patterns = validation_patterns()
    assert patterns["q0"] == "1" + "0" * 97
    assert patterns["q97"] == "0" * 97 + "1"
    for name in ("non_palindromic_blocks", "alternating_q0_one"):
        assert patterns[name] != patterns[name][::-1]
    mapping = build_measurement_mapping(
        logical_to_classical={i: i for i in range(98)},
        sdk_string_order="lsb_left",
        register_layout=[{"name": "out", "classical_indices": list(range(98))}],
    )
    prepared = patterns["q0_q7_q31_q64_q97"]
    assert validate_observed_case("sparse", prepared, prepared, mapping).mapping_correct
    assert not validate_observed_case("reversed", prepared, prepared[::-1], mapping).mapping_correct


def test_offline_mapping_run_prepares_all_cases(tmp_path: Path) -> None:
    config = tmp_path / "configs/compilation.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        """schema_version: '2.0'
source_circuit: unused.qasm
backend: {provider: quantinuum, device_name: null, mode: compile_only}
compiler: {optimization_level: 1, timeout_seconds: 30, preserve_qubit_names: true, allow_implicit_swaps: false}
measurement: {append_measure_all: true}
output: {directory: results/compilation, export_qasm: true}
"""
    )
    report = run_mapping_validation(tmp_path, target=None, mode="offline", config_path=config)
    assert report.status == "incomplete"
    assert report.total_cases == 6
    assert len(list((tmp_path / "results/mapping_validation/cases").glob("*.qasm"))) == 6


def test_compilation_unit_map_is_required_and_traced() -> None:
    from pytket import Circuit

    circuit = Circuit(2, 2)
    circuit.Measure(0, 0)
    circuit.Measure(1, 1)
    artifact = CompiledCircuitArtifact(
        circuit=circuit,
        initial_map={"q[0]": "q[0]", "q[1]": "q[1]"},
        final_map={"q[0]": "q[0]", "q[1]": "q[1]"},
        effective_options={"allow_implicit_swaps": False},
    )
    mapping = trace_measurements(artifact, 2)
    assert mapping.complete and mapping.unknown_permutation_count == 0
    assert [entry.compiled_qubit_name for entry in mapping.entries] == ["q[0]", "q[1]"]
    with pytest.raises(RuntimeError, match="incomplete"):
        trace_measurements(
            artifact.__class__(
                circuit=circuit,
                initial_map=artifact.initial_map,
                final_map={"q[0]": "q[0]"},
                effective_options=artifact.effective_options,
            ),
            2,
        )


def test_duplicate_classical_destination_is_rejected() -> None:
    from pytket import Circuit

    circuit = Circuit(2, 1)
    circuit.Measure(0, 0)
    circuit.Measure(1, 0)
    artifact = CompiledCircuitArtifact(
        circuit=circuit,
        initial_map={"q[0]": "q[0]", "q[1]": "q[1]"},
        final_map={"q[0]": "q[0]", "q[1]": "q[1]"},
        effective_options={},
    )
    with pytest.raises(RuntimeError, match="reused"):
        trace_measurements(artifact, 2)
