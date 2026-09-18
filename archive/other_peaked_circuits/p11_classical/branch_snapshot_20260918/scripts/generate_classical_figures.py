#!/usr/bin/env python3
"""Generate deterministic, dependency-free SVG figures from classical_index.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/classical/figures"
COLORS = {"SOLVED_CLASSICAL": "#198754", "VERIFIED_CONTROL": "#0d6efd", "UNRESOLVED": "#dc3545", "METHOD_EXHAUSTED": "#6c757d"}


def svg(title: str, body: str, width: int = 900, height: int = 500) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>text{{font-family:Arial,sans-serif;fill:#202124}}.title{{font-size:22px;font-weight:700}}.axis{{stroke:#777;stroke-width:1}}.grid{{stroke:#ddd;stroke-width:1}}.label{{font-size:14px}}.small{{font-size:12px}}</style>
<rect width="100%" height="100%" fill="white"/><text x="40" y="35" class="title">{title}</text>{body}</svg>'''


def main() -> None:
    records = json.loads((ROOT / "results/classical_index.json").read_text())["records"]
    OUT.mkdir(parents=True, exist_ok=True)
    # Figure 1: circuit size versus two-qubit work count.
    x0, y0, w, h = 80, 70, 760, 350
    maxg = max(r["two_qubit_gate_count"] for r in records)
    points = []
    for i, r in enumerate(records):
        x = x0 + i * (w / (len(records) - 1))
        y = y0 + h - r["two_qubit_gate_count"] / maxg * h
        color = COLORS.get(r["status"], "#333")
        points.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{color}"/><text x="{x-10:.1f}" y="{y+28:.1f}" class="label">{r["problem"]}</text><text x="{x-22:.1f}" y="{y-14:.1f}" class="small">{r["two_qubit_gate_count"]}</text>')
    body = f'<line x1="{x0}" y1="{y0+h}" x2="{x0+w}" y2="{y0+h}" class="axis"/><line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0+h}" class="axis"/><text x="350" y="475" class="label">problems in campaign order</text><text x="12" y="250" transform="rotate(-90 12 250)" class="label">two-qubit/work gates</text>{"".join(points)}'
    (OUT / "circuit_size_status.svg").write_text(svg("Classical campaign size and outcome", body))
    # Figure 2: outcome heatmap for method families.
    methods = [("MPO/MPS", "P5/P9 controls", "P6 unresolved", "P8 tail"), ("routing", "pass", "stall", "804"), ("structural", "diagnostic", "no candidate", "diagnostic")]
    cells = []
    for row, (name, a, b, c) in enumerate(methods):
        cells.append(f'<text x="30" y="{120+row*75}" class="label">{name}</text>')
        for col, val in enumerate((a, b, c)):
            fill = "#d1e7dd" if col == 0 else ("#f8d7da" if col == 1 else "#fff3cd")
            cells.append(f'<rect x="180" y="{90+row*75}" width="210" height="45" fill="{fill}" stroke="white"/><text x="190" y="118" class="small">{val}</text>')
    body = "".join(cells) + '<text x="180" y="50" class="label">P5/P9 controls</text><text x="390" y="50" class="label">P6</text><text x="600" y="50" class="label">P8</text>'
    (OUT / "method_outcome_heatmap.svg").write_text(svg("Method-family outcome summary", body, 900, 350))
    # Figure 3: P6 cutoff tradeoff.
    vals = [("6e-4", 148, 0.0), ("1e-3", 180, 0.0), ("1.875e-3", 2593, 0.001), ("2e-3", 2593, 0.001)]
    bars = []
    for i, (label, gates, _peak) in enumerate(vals):
        x = 100 + i * 185
        bh = gates / 2593 * 300
        bars.append(f'<rect x="{x}" y="{390-bh:.1f}" width="100" height="{bh:.1f}" fill="#6c757d"/><text x="{x+5}" y="420" class="small">{label}</text><text x="{x+20}" y="{380-bh:.1f}" class="small">{gates}/{2593}</text>')
    body = '<line x1="70" y1="390" x2="850" y2="390" class="axis"/><text x="320" y="465" class="label">cutoff</text><text x="10" y="240" transform="rotate(-90 10 240)" class="label">gates completed</text>' + "".join(bars) + '<text x="70" y="55" class="small">Flat readout at the two completing settings: peak fraction ≈ 0.001</text>'
    (OUT / "p6_cutoff_progress_fidelity.svg").write_text(svg("P6 cutoff, traversal, and readout tradeoff", body, 900, 500))


if __name__ == "__main__":
    main()
