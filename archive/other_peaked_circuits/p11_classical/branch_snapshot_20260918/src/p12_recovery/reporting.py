from __future__ import annotations

import importlib.metadata
import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

# Reporting only saves PNGs.  Avoid the native macOS GUI backend, which can
# abort a headless CLI/test process while creating its first figure.
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
from pydantic import BaseModel

from .hashing import sha256_file
from .models import ReportBase, RunManifest

PACKAGES = [
    "p12-helios-recovery",
    "numpy",
    "scipy",
    "pandas",
    "networkx",
    "pydantic",
    "PyYAML",
    "matplotlib",
    "typer",
    "rich",
    "pytket",
    "pytket-quantinuum",
    "pytket-qir",
    "pyqir",
    "qnexus",
    "pytket-qiskit",
    "qiskit",
]


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def git_state(root: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
        )
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def git_dirty_paths(root: Path) -> list[str]:
    try:
        output = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    paths: list[str] = []
    for line in output.splitlines():
        value = line[3:].strip()
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.strip('"'))
    return paths


def repository_root(path: Path) -> Path | None:
    candidate = path if path.is_dir() else path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    try:
        output = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=candidate,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        return Path(output).resolve()
    except (OSError, subprocess.CalledProcessError):
        return None


def relative_identifier(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"external:{resolved.name}"


def _sanitize_paths(value: Any, root: Path | None) -> Any:
    if isinstance(value, dict):
        return {
            str(_sanitize_paths(key, root)): _sanitize_paths(item, root)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_paths(item, root) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_paths(item, root) for item in value]
    if isinstance(value, str) and Path(value).is_absolute():
        path = Path(value)
        return relative_identifier(path, root) if root else f"external:{path.name}"
    return value


def write_json(path: Path, value: BaseModel | dict[str, Any] | list[Any]) -> None:
    root = repository_root(path)
    if isinstance(value, ReportBase) and root:
        commit, dirty = git_state(root)
        value = value.model_copy(update={"git_commit": commit, "git_dirty": dirty})
    payload: Any = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    payload = _sanitize_paths(payload, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def inspection_markdown(report: BaseModel) -> str:
    data = report.model_dump(mode="json")
    gates = data["gates"]
    graph = data["interaction_graph"]
    return f"""# P12 circuit inspection

Generated: {data["created_at"]}

## Identity and width

- Source SHA-256: `{data["source_sha256"]}`
- Parser: {data["parser"]} {data["parser_version"]}
- Qubits: {data["number_of_qubits"]}
- Classical bits: {data["number_of_classical_bits"]}
- Source measurements: {data["source_contains_measurements"]}

## Gates and depth

- Total operations: {gates["total_operations"]}
- Gate counts: `{json.dumps(gates["counts_by_gate"], sort_keys=True)}`
- One-qubit gates: {gates["one_qubit_gates"]}
- Two-qubit gates: {gates["two_qubit_gates"]}
- Total / 1q / 2q depth: {gates["circuit_depth"]} / {gates["one_qubit_depth"]} / {gates["two_qubit_depth"]}
- Unsupported instructions: `{gates["unsupported_instructions"]}`

## Interaction graph

- Nodes / active nodes / edges: {graph["number_of_nodes"]} / {graph["active_nodes"]} / {graph["number_of_edges"]}
- Connected components: {graph["connected_components"]}
- Fully connected: {graph["fully_connected"]}
- Degree min / mean / median / max: {graph["degree_min"]:.3f} / {graph["degree_mean"]:.3f} / {graph["degree_median"]:.3f} / {graph["degree_max"]:.3f}

Depth definition: {data["depth_definition"]}.

This is structural inspection, not a claim of full semantic equivalence or hardware validity.
"""


def save_inspection_figures(report: BaseModel, figures_dir: Path) -> None:
    data = report.model_dump()
    graph = data["interaction_graph"]
    frequent = graph["frequent_pairs"]
    figures_dir.mkdir(parents=True, exist_ok=True)
    # Plot all logical-qubit interaction degrees from the machine-readable histogram.
    plt.figure(figsize=(8, 5))
    degree_values = [
        int(degree) for degree, count in graph["degree_histogram"].items() for _ in range(count)
    ]
    plt.hist(
        degree_values,
        bins=range(min(degree_values), max(degree_values) + 2),
        color="#3b6fb6",
        edgecolor="black",
        align="left",
    )
    plt.title("P12 logical-qubit interaction-degree distribution")
    plt.xlabel("Distinct interacting neighbors per logical qubit (degree)")
    plt.ylabel("Logical qubits (count)")
    plt.figtext(0.01, 0.01, "Source: results/inspection/inspection_report.json", fontsize=7)
    plt.tight_layout()
    plt.savefig(
        figures_dir / "interaction_graph_degree_histogram.png",
        dpi=300,
        metadata={"Source": "results/inspection/inspection_report.json"},
    )
    plt.close()
    labels = [f"q{x['qubits'][0]}-q{x['qubits'][1]}" for x in frequent]
    counts = [x["count"] for x in frequent]
    plt.figure(figsize=(10, 6))
    positions = np.arange(len(labels))
    plt.barh(positions, counts, color="#8a5fb5")
    plt.yticks(positions, labels)
    plt.gca().invert_yaxis()
    plt.title("Most frequent P12 two-qubit interaction pairs")
    plt.xlabel("Interaction count (gates)")
    plt.ylabel("Logical-qubit pair")
    plt.figtext(0.01, 0.01, "Source: results/inspection/inspection_report.json", fontsize=7)
    plt.tight_layout()
    plt.savefig(
        figures_dir / "two_qubit_pair_frequency.png",
        dpi=300,
        metadata={"Source": "results/inspection/inspection_report.json"},
    )
    plt.close()


def write_manifest(
    root: Path,
    *,
    command: str,
    arguments: list[str],
    start: datetime,
    exit_status: int,
    inputs: list[Path] | None = None,
    outputs: list[Path] | None = None,
    config: Path | None = None,
    seed: int | None = None,
    backend_mode: str = "offline",
    credentials_detected: bool = False,
) -> Path:
    end = datetime.now(UTC)
    commit, dirty = git_state(root)
    run_id = f"{start.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    input_paths = {
        relative_identifier(path, root): sha256_file(path)
        for path in (inputs or [])
        if path.is_file()
    }
    output_paths = {
        relative_identifier(path, root): sha256_file(path)
        for path in (outputs or [])
        if path.is_file()
    }
    manifest = RunManifest(
        run_id=run_id,
        command=command,
        arguments=arguments,
        start_timestamp=start,
        end_timestamp=end,
        exit_status=exit_status,
        git_commit=commit,
        git_dirty=dirty,
        dirty_working_tree=dirty,
        package_versions=package_versions(),
        input_paths=input_paths,
        output_paths=output_paths,
        configuration_path=relative_identifier(config, root) if config else None,
        configuration_hash=sha256_file(config) if config and config.is_file() else None,
        random_seed=seed,
        backend_mode=backend_mode,
        credentials_detected=credentials_detected,
        input_hashes=input_paths,
    )
    path = root / "results/manifests" / f"{run_id}.json"
    write_json(path, manifest)
    return path
