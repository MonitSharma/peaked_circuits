import json
from pathlib import Path

import pytest

from p12_recovery.counts_io import (
    load_aggregated_counts,
    load_count_pairs,
    load_shots_jsonl,
    write_aggregated_counts,
    write_shots_jsonl,
)


def test_counts_roundtrip_and_metadata(tmp_path: Path) -> None:
    path = tmp_path / "counts.json"
    write_aggregated_counts(path, {"001": 2, "111": 1}, metadata={"provider": "fixture"})
    value = load_aggregated_counts(path)
    assert value["shots"] == 3
    assert value["metadata"]["provider"] == "fixture"
    assert "001" in value["counts"]


def test_invalid_sum_and_explicit_duplicate_merge(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "bit_order": "canonical",
                "number_of_qubits": 2,
                "shots": 3,
                "counts": {"00": 2},
            }
        )
    )
    with pytest.raises(ValueError):
        load_aggregated_counts(path)
    assert load_count_pairs([("00", 1), ("00", 2)], number_of_qubits=2, merge_duplicates=True) == {
        "00": 3
    }
    with pytest.raises(ValueError):
        load_count_pairs([("00", 1), ("00", 2)], number_of_qubits=2, merge_duplicates=False)


def test_individual_shot_jsonl_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "shots.jsonl"
    write_shots_jsonl(path, [("00", "00"), ("01", "10")])
    records = load_shots_jsonl(path, number_of_qubits=2)
    assert [record["shot_index"] for record in records] == [0, 1]
    assert records[1]["canonical_bitstring"] == "10"
    path.write_text(path.read_text().replace('"shot_index": 1', '"shot_index": 3'))
    with pytest.raises(ValueError):
        load_shots_jsonl(path, number_of_qubits=2)
