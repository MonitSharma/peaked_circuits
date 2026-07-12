import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast


def validate_canonical_bitstring(bitstring: str, number_of_qubits: int = 98) -> None:
    if len(bitstring) != number_of_qubits:
        raise ValueError(f"Expected {number_of_qubits} bits, received {len(bitstring)}")
    if set(bitstring) - {"0", "1"}:
        raise ValueError("Bitstrings must contain only 0 and 1")


def validate_counts(counts: Mapping[str, int], number_of_qubits: int) -> int:
    if not counts:
        raise ValueError("Counts cannot be empty")
    total = 0
    for bitstring, count in counts.items():
        validate_canonical_bitstring(bitstring, number_of_qubits)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Count values must be nonnegative integers")
        total += count
    if total <= 0:
        raise ValueError("Counts must contain at least one shot")
    return total


def load_aggregated_counts(path: Path, *, merge_duplicates: bool = False) -> dict[str, Any]:
    # JSON objects cannot faithfully carry duplicate keys; explicit merging is only
    # supported through load_count_pairs below.
    del merge_duplicates
    payload = json.loads(path.read_text())
    required = {"schema_version", "bit_order", "number_of_qubits", "shots", "counts"}
    if not required.issubset(payload):
        raise ValueError(f"Counts document is missing fields: {sorted(required - set(payload))}")
    total = validate_counts(payload["counts"], payload["number_of_qubits"])
    if total != payload["shots"]:
        raise ValueError(f"Count sum {total} does not equal declared shots {payload['shots']}")
    payload.setdefault("metadata", {})
    return cast(dict[str, Any], payload)


def load_count_pairs(
    pairs: Iterable[tuple[str, int]], *, number_of_qubits: int, merge_duplicates: bool
) -> dict[str, int]:
    result: Counter[str] = Counter()
    seen: set[str] = set()
    for bitstring, count in pairs:
        validate_canonical_bitstring(bitstring, number_of_qubits)
        if bitstring in seen and not merge_duplicates:
            raise ValueError("Duplicate bitstring requires merge_duplicates=True")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Count values must be nonnegative integers")
        seen.add(bitstring)
        result[bitstring] += count
    validate_counts(result, number_of_qubits)
    return dict(result)


def write_aggregated_counts(
    path: Path,
    counts: Mapping[str, int],
    *,
    bit_order: str = "canonical",
    metadata: dict[str, Any] | None = None,
) -> None:
    number = len(next(iter(counts))) if counts else 0
    shots = validate_counts(counts, number)
    payload = {
        "schema_version": "1.0",
        "bit_order": bit_order,
        "number_of_qubits": number,
        "shots": shots,
        "counts": dict(sorted(counts.items())),
        "metadata": metadata or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_shots_jsonl(path: Path, raw_and_canonical: Iterable[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for index, (raw, canonical) in enumerate(raw_and_canonical):
            handle.write(
                json.dumps(
                    {"shot_index": index, "raw_bitstring": raw, "canonical_bitstring": canonical}
                )
                + "\n"
            )


def load_shots_jsonl(path: Path, *, number_of_qubits: int = 98) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Shot record file does not exist: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"Empty JSONL record at line {line_number}")
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"Shot record {line_number} must be an object")
        if record.get("shot_index") != len(records):
            raise ValueError("Shot indices must be unique, contiguous, and start at zero")
        raw = record.get("raw_bitstring")
        canonical = record.get("canonical_bitstring")
        if not isinstance(raw, str) or set("".join(raw.split())) - {"0", "1"}:
            raise ValueError("Raw shot bitstrings must contain only binary symbols and separators")
        if not isinstance(canonical, str):
            raise ValueError("Every shot requires a canonical_bitstring")
        validate_canonical_bitstring(canonical, number_of_qubits)
        records.append(record)
    if not records:
        raise ValueError("Shot record file cannot be empty")
    return records
