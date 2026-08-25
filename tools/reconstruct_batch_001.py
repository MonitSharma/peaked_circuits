"""Target-blind, hash-addressed reconstruction of Batch 001."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


EXCLUDED_CYCLES = [37, 82, 120, 165, 201]
OUTPUT_RE = re.compile(r"^OUTPUT\tRESULT\t([01])\t(m\d{3}\[0\])(END\t.*)?$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cycle_hash(cycle: list[tuple[str, str]]) -> str:
    return hashlib.sha256("\n".join(f"{label}={value}" for label, value in cycle).encode()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_path = root / "hardware_campaign/batch_001/provider/raw_result.json"
    mapping = json.loads((root / "results/nexus/emulator_mapping/provider_output_mapping.json").read_text())
    canonical_by_provider = {entry["provider_field"]: entry["canonical_position"] for entry in mapping["entries"]}
    records = []
    for line in raw_path.read_text().splitlines():
        match = OUTPUT_RE.match(line)
        if match:
            records.append((match.group(2), match.group(1)))
    if len(records) != 205 * 98:
        raise RuntimeError(f"Expected 205*98 records, found {len(records)}")
    cycles = [records[index : index + 98] for index in range(0, len(records), 98)]
    if any(len(set(label for label, _ in cycle)) != 98 for cycle in cycles):
        raise RuntimeError("At least one cycle does not contain 98 unique provider labels")
    hashes = [cycle_hash(cycle) for cycle in cycles]
    if any(hashes[index] != hashes[0] for index in EXCLUDED_CYCLES):
        raise RuntimeError("Excluded cycles are not exact replicas of cycle 0")
    retained = [cycle for index, cycle in enumerate(cycles) if index not in EXCLUDED_CYCLES]
    shots = []
    for cycle in retained:
        by_position = {canonical_by_provider[label]: value for label, value in cycle}
        shots.append("".join(by_position[index] for index in range(98)))
    counts = Counter(shots)
    out = root / "hardware_campaign/batch_001/reconstruction"
    out.mkdir(parents=True, exist_ok=True)
    (out / "reconstructed_200_shots.jsonl").write_text(
        "".join(json.dumps({"shot_index": index, "canonical_bitstring": shot}) + "\n" for index, shot in enumerate(shots))
    )
    (out / "reconstructed_counts.json").write_text(json.dumps({
        "schema_version": "1.0", "bit_order": "canonical", "number_of_qubits": 98,
        "shots": len(shots), "counts": dict(sorted(counts.items())),
        "metadata": {"reconstruction": "exclude exact segment-overlap replicas", "excluded_cycles": EXCLUDED_CYCLES},
    }, indent=2, sort_keys=True) + "\n")
    manifest = {
        "schema_version": "1.0", "algorithm": "batch001_segment_overlap_v1",
        "raw_payload_sha256": sha256(raw_path), "raw_cycle_count": len(cycles),
        "reconstructed_shot_count": len(shots), "excluded_cycles": EXCLUDED_CYCLES,
        "segment_overlap_sha256": hashes[0], "cycle_sha256": hashes,
        "mapping_path": "results/nexus/emulator_mapping/provider_output_mapping.json",
        "mapping_sha256": sha256(root / "results/nexus/emulator_mapping/provider_output_mapping.json"),
        "reconstructed_counts_sha256": sha256(out / "reconstructed_counts.json"),
        "reconstructed_shots_sha256": sha256(out / "reconstructed_200_shots.jsonl"),
        "external_target_scored": False,
    }
    (out / "reconstruction_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    files = [out / name for name in ("reconstruction_manifest.json", "reconstructed_counts.json", "reconstructed_200_shots.jsonl")]
    (out / "SHA256SUMS").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files))
    print(json.dumps({"retained_shots": len(shots), "excluded_cycles": EXCLUDED_CYCLES, "unique_strings": len(counts)}, indent=2))


if __name__ == "__main__":
    main()
