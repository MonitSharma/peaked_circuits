from __future__ import annotations

import importlib.metadata
from pathlib import Path

from .models import CostEstimateItem, CostEstimateReport
from .reporting import write_json


def estimate_costs(root: Path, target: str, shots: list[int]) -> CostEstimateReport:
    if not shots or any(value <= 0 for value in shots):
        raise ValueError("Shot estimates must be positive integers")
    try:
        version = importlib.metadata.version("pytket-quantinuum")
    except importlib.metadata.PackageNotFoundError:
        version = None
    # pytket-quantinuum 0.59.1 exposes no stable public cost method on QuantinuumBackend.
    report = CostEstimateReport(
        status="unsupported",
        target=target,
        estimates=[CostEstimateItem(shots=value) for value in shots],
        reason=(
            "The installed QuantinuumBackend exposes no public cost API. No HQC formula was invented; "
            "obtain provider or syntax-checker provenance before protocol freeze."
        ),
        sdk_version=version,
        provenance="Inspected QuantinuumBackend public API; cost attribute is absent",
        manual_action_required=True,
    )
    output = root / "results/cost"
    write_json(output / "cost_estimate.json", report)
    (output / "cost_estimate.md").write_text(
        f"# Cost estimate\n\nStatus: **unsupported**\n\nTarget: `{target}`\n\n{report.reason}\n"
    )
    return report
