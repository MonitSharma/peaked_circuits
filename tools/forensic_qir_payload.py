"""Target-blind forensic inspection of a labeled Nexus QIR payload."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


OUTPUT_RE = re.compile(r"^OUTPUT\tRESULT\t([01])\t(m\d{3}\[0\])$")
EXPECTED = {f"m{index:03d}[0]" for index in range(98)}


def inspect(path: Path) -> dict[str, object]:
    text = path.read_text()
    lines = text.splitlines()
    records: list[tuple[str, str]] = []
    malformed = []
    for line_number, line in enumerate(lines, start=1):
        if not line.startswith("OUTPUT\tRESULT"):
            continue
        match = OUTPUT_RE.match(line)
        if match is None:
            malformed.append(line_number)
        else:
            records.append((match.group(2), match.group(1)))

    cycles = [records[index : index + 98] for index in range(0, len(records), 98)]
    cycle_reports = []
    for index, cycle in enumerate(cycles):
        labels = [label for label, _ in cycle]
        cycle_reports.append(
            {
                "cycle_index": index,
                "record_count": len(cycle),
                "complete_label_set": len(cycle) == 98 and set(labels) == EXPECTED and len(set(labels)) == 98,
                "sha256": hashlib.sha256("\n".join(f"{label}={value}" for label, value in cycle).encode()).hexdigest(),
            }
        )

    starts = [index for index, line in enumerate(lines) if line == "START"]
    framed_groups = []
    for start, end in zip(starts, starts[1:] + [len(lines)]):
        group = lines[start:end]
        outputs = [line for line in group if line.startswith("OUTPUT\tRESULT\t")]
        framed_groups.append({"output_records": len(outputs), "has_end": any(line.startswith("END\t") for line in group)})

    return {
        "source_path": str(path),
        "payload_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "output_record_count": len(records),
        "record_width": 98,
        "record_cycle_count": len(cycles),
        "complete_record_cycles": sum(bool(item["complete_label_set"]) for item in cycle_reports),
        "malformed_output_lines": malformed,
        "start_count": len(starts),
        "framed_groups_with_98_outputs": sum(item["output_records"] == 98 for item in framed_groups),
        "framed_groups_with_end": sum(bool(item["has_end"]) for item in framed_groups),
        "cycle_sha256": [item["sha256"] for item in cycle_reports],
        "cycle_reports": cycle_reports,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "hardware_campaign/batch_001/provider/raw_result.json"
    report = inspect(source)
    submitted_input = root / "hardware_campaign/batch_001/provider/submitted_input.bc"
    report["submitted_input_bitcode_sha256"] = hashlib.sha256(submitted_input.read_bytes()).hexdigest()
    report["frozen_bitcode_sha256"] = hashlib.sha256((root / "results/qir/p12.bc").read_bytes()).hexdigest()
    report["submitted_input_matches_frozen"] = report["submitted_input_bitcode_sha256"] == report["frozen_bitcode_sha256"]
    output = root / "results/prephysical/batch_001_qir_forensic.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("output_record_count", "record_cycle_count", "complete_record_cycles", "start_count", "framed_groups_with_end")}, indent=2))


if __name__ == "__main__":
    main()
