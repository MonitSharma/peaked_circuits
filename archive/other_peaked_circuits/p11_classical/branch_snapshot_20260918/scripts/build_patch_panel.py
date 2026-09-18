#!/usr/bin/env python3
"""Freeze a deterministic P9 dependency-aware patch panel."""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compiler.local_synthesis import extract_dependency_blocks
from structural.patch_unitary import patch_unitary
from structural.qasm_events import parse_qasm

SEED = 20260821
QASM = Path("data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm")
OUT = Path("results/p11_final_campaign/P9_PATCH_PANEL.json")


def unitary_hash(matrix: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(matrix).view(np.float64).tobytes()).hexdigest()


def choose(blocks, n, midpoint, rng):
    near = [b for b in blocks if abs((b.start + b.stop) / 2 - midpoint) <= 0.25 * midpoint]
    away = [b for b in blocks if abs((b.start + b.stop) / 2 - midpoint) > 0.25 * midpoint]
    # Stratify by entangler count, then sample deterministically within each region.
    def ranked(pool):
        groups = {}
        for block in pool:
            groups.setdefault(min(block.old_two_qubit, 5), []).append(block)
        for group in groups.values():
            rng.shuffle(group)
        return [block for count in sorted(groups) for block in groups[count]]
    selected = []
    for pool in (ranked(near), ranked(away)):
        selected.extend(pool[: n // 2])
    return selected


def main() -> None:
    rng = random.Random(SEED)
    circuit = parse_qasm(QASM)
    midpoint = len(circuit.events) / 2
    rows = []
    for size, near_count, away_count in ((3, 20, 20), (4, 10, 10)):
        blocks = [block for block in extract_dependency_blocks(circuit, size) if len(block.wires) == size]
        near = [b for b in blocks if abs((b.start + b.stop) / 2 - midpoint) <= 0.25 * midpoint]
        away = [b for b in blocks if abs((b.start + b.stop) / 2 - midpoint) > 0.25 * midpoint]
        for region, pool, count in (("midpoint", near, near_count), ("away", away, away_count)):
            by_count = {}
            for block in pool:
                by_count.setdefault(min(block.old_two_qubit, 5), []).append(block)
            for group in by_count.values():
                rng.shuffle(group)
            ordered = []
            keys = sorted(by_count)
            while len(ordered) < count and keys:
                progressed = False
                for key in keys:
                    if by_count[key]:
                        ordered.append(by_count[key].pop())
                        progressed = True
                        if len(ordered) == count:
                            break
                if not progressed:
                    break
            chosen = ordered
            if len(chosen) < count:
                raise RuntimeError(f"insufficient {region} q={size} blocks: {len(chosen)}")
            for rank, block in enumerate(chosen):
                matrix = patch_unitary(block.events, block.wires)
                rows.append({
                    "panel_id": f"q{size}_{region}_{rank:02d}",
                    "q": size,
                    "region": region,
                    "start_event": block.start,
                    "stop_event": block.stop,
                    "wires": list(block.wires),
                    "old_2q": block.old_two_qubit,
                    "event_count": len(block.events),
                    "unitary_sha256": unitary_hash(matrix),
                })
    payload = {"schema": "p11-p9-patch-panel-v1", "seed": SEED, "qasm": str(QASM), "qasm_sha256": hashlib.sha256(QASM.read_bytes()).hexdigest(), "frozen": True, "extractor": "dependency-aware causal boundary extractor", "panel": rows}
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"blocks": len(rows), "q3": sum(row["q"] == 3 for row in rows), "q4": sum(row["q"] == 4 for row in rows), "counts": {str(count): sum(row["old_2q"] == count for row in rows) for count in sorted({row["old_2q"] for row in rows})}}, sort_keys=True))


if __name__ == "__main__":
    main()
