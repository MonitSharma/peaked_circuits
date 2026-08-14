from __future__ import annotations

from typing import Any

from .models import MeasurementEntry, MeasurementMapping


def _bits(raw: str) -> str:
    cleaned = "".join(raw.split())
    if not cleaned or set(cleaned) - {"0", "1"}:
        raise ValueError("Raw bitstring must contain only binary symbols and separators")
    return cleaned


def _classical_raw_positions(
    register_layout: list[dict[str, Any]], sdk_string_order: str
) -> dict[int, int]:
    if sdk_string_order not in {"msb_left", "lsb_left"}:
        raise ValueError("sdk_string_order must be exactly 'msb_left' or 'lsb_left'")
    if not register_layout:
        raise ValueError("register_layout cannot be empty")
    flattened: list[int] = []
    seen: set[int] = set()
    for register in register_layout:
        indices = register.get("classical_indices")
        if not isinstance(indices, list) or not indices:
            raise ValueError("Every register needs an unambiguous classical_indices list")
        for index in indices:
            if not isinstance(index, int) or index in seen:
                raise ValueError("Classical register indices must be unique integers")
            seen.add(index)
        flattened.extend(indices if sdk_string_order == "lsb_left" else reversed(indices))
    if sdk_string_order == "msb_left":
        # Provider display commonly reverses both register sequence and bits per register.
        flattened = []
        for register in reversed(register_layout):
            flattened.extend(reversed(register["classical_indices"]))
    return {classical: position for position, classical in enumerate(flattened)}


def classical_raw_positions(
    register_layout: list[dict[str, Any]], sdk_string_order: str
) -> dict[int, int]:
    return _classical_raw_positions(register_layout, sdk_string_order)


def build_measurement_mapping(
    *,
    logical_to_classical: dict[int, int],
    sdk_string_order: str,
    register_layout: list[dict[str, Any]],
    logical_to_physical: dict[int, int] | None = None,
    logical_to_compiled_name: dict[int, str] | None = None,
    logical_to_compiled_index: dict[int, int | None] | None = None,
    mapping_source: str = "explicit_logical_to_classical",
    mapping_confidence: str = "high",
) -> MeasurementMapping:
    number = len(logical_to_classical)
    if set(logical_to_classical) != set(range(number)):
        raise ValueError("Logical-to-classical mapping must cover contiguous logical qubits")
    if len(set(logical_to_classical.values())) != number:
        raise ValueError("Duplicate classical bits are not allowed")
    raw_positions = _classical_raw_positions(register_layout, sdk_string_order)
    if not set(logical_to_classical.values()).issubset(raw_positions):
        raise ValueError("Measurement mapping references missing classical bits")
    if logical_to_physical is not None and set(logical_to_physical) != set(range(number)):
        raise ValueError("Logical-to-physical mapping is incomplete")
    classical_registers: dict[int, str] = {}
    for register in register_layout:
        for classical in register["classical_indices"]:
            classical_registers[classical] = str(register.get("name", "unnamed"))
    entries = [
        MeasurementEntry(
            logical_qubit_index=logical,
            logical_qubit_name=f"q[{logical}]",
            compiled_qubit_name=(logical_to_compiled_name or {}).get(logical, f"q[{logical}]"),
            compiled_qubit_index=(logical_to_compiled_index or {}).get(logical, logical),
            physical_qubit_index=(logical_to_physical or {}).get(logical),
            classical_register_name=classical_registers[classical],
            classical_bit_index=classical,
            raw_provider_position=raw_positions[classical],
            canonical_position=logical,
            mapping_source=mapping_source,
            mapping_confidence=mapping_confidence,  # type: ignore[arg-type]
        )
        for logical, classical in sorted(logical_to_classical.items())
    ]
    return MeasurementMapping(
        number_of_qubits=number,
        sdk_string_order=sdk_string_order,
        register_layout=register_layout,
        entries=entries,
    )


def raw_bitstring_to_canonical(
    raw: str,
    *,
    logical_to_classical: dict[int, int],
    sdk_string_order: str,
    register_layout: list[dict[str, Any]],
) -> str:
    cleaned = _bits(raw)
    mapping = build_measurement_mapping(
        logical_to_classical=logical_to_classical,
        sdk_string_order=sdk_string_order,
        register_layout=register_layout,
    )
    expected = sum(len(r["classical_indices"]) for r in register_layout)
    if len(cleaned) != expected:
        raise ValueError(
            f"Raw bitstring length {len(cleaned)} does not match layout length {expected}"
        )
    result = ["?"] * mapping.number_of_qubits
    for entry in mapping.entries:
        result[entry.canonical_string_position] = cleaned[entry.raw_string_position]
    if "?" in result:
        raise ValueError("Incomplete measurement mapping")
    return "".join(result)


def canonical_to_raw_bitstring(canonical: str, mapping: MeasurementMapping) -> str:
    canonical = _bits(canonical)
    raw_length = sum(len(r["classical_indices"]) for r in mapping.register_layout)
    if len(canonical) != mapping.number_of_qubits:
        raise ValueError("Canonical string length does not match mapping")
    raw = ["0"] * raw_length
    for entry in mapping.entries:
        raw[entry.raw_string_position] = canonical[entry.canonical_string_position]
    return "".join(raw)


def provider_value_to_raw_string(value: Any) -> str:
    """Convert provider strings or flat binary arrays without changing order."""
    if isinstance(value, str):
        return _bits(value)
    if isinstance(value, (list, tuple)):
        if any(item not in (0, 1, "0", "1") for item in value):
            raise ValueError("Provider arrays must contain only binary values")
        return "".join(str(item) for item in value)
    raise ValueError(f"Unsupported provider result value: {type(value).__name__}")


def raw_value_to_canonical(value: Any, mapping: MeasurementMapping) -> str:
    raw = provider_value_to_raw_string(value)
    raw_length = sum(len(r["classical_indices"]) for r in mapping.register_layout)
    if len(raw) != raw_length:
        raise ValueError(
            f"Provider output width {len(raw)} does not match layout width {raw_length}"
        )
    result = ["?"] * mapping.number_of_qubits
    for entry in mapping.entries:
        result[entry.canonical_position] = raw[entry.raw_provider_position]
    if "?" in result or len(result) != mapping.number_of_qubits:
        raise ValueError("Measurement mapping is incomplete")
    return "".join(result)
