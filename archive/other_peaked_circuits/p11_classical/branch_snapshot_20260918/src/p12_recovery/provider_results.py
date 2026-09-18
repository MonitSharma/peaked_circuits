from __future__ import annotations

import importlib
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .bit_ordering import provider_value_to_raw_string, raw_value_to_canonical
from .bootstrap import bootstrap_recovery
from .counts_io import write_aggregated_counts, write_shots_jsonl
from .hashing import hash_config, sha256_file
from .models import (
    BootstrapReport,
    CanonicalResult,
    MeasurementMapping,
    ProviderJobMetadata,
    ProviderRawResult,
    RecoveryReport,
)
from .recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)
from .reporting import package_versions, write_json


def load_provider_result(path: Path) -> ProviderRawResult:
    if not path.is_file():
        raise FileNotFoundError(f"Provider result file does not exist: {path}")
    return ProviderRawResult.model_validate_json(path.read_text())


def normalize_provider_result(
    raw: ProviderRawResult, mapping: MeasurementMapping
) -> CanonicalResult:
    if not mapping.complete or mapping.unknown_permutation_count:
        raise ValueError("Provider normalization requires a complete, permutation-resolved mapping")
    if raw.raw_result_order != mapping.sdk_string_order:
        raise ValueError(
            f"Provider order {raw.raw_result_order} does not match mapping order {mapping.sdk_string_order}"
        )
    if _layout_signature(raw.raw_register_layout) != _layout_signature(mapping.register_layout):
        raise ValueError("Provider register layout does not exactly match the compiled mapping")
    canonical_counts: Counter[str] = Counter()
    for provider_value, count in raw.raw_counts.items():
        if count < 0:
            raise ValueError("Provider counts cannot be negative")
        canonical = raw_value_to_canonical(provider_value, mapping)
        if len(canonical) != 98:
            raise ValueError("Canonical provider output is not exactly 98 bits")
        canonical_counts[canonical] += count
    canonical_shots: list[str] = []
    for provider_value in raw.raw_shots:
        canonical = raw_value_to_canonical(provider_value, mapping)
        if len(canonical) != 98:
            raise ValueError("Canonical provider shot is not exactly 98 bits")
        canonical_shots.append(canonical)
    count_total = sum(canonical_counts.values())
    if count_total and count_total != raw.returned_shots:
        raise ValueError("Provider count total does not equal returned_shots")
    if canonical_shots and len(canonical_shots) != raw.returned_shots:
        raise ValueError("Provider shot record count does not equal returned_shots")
    if not canonical_counts and canonical_shots:
        canonical_counts.update(canonical_shots)
    if not canonical_counts:
        raise ValueError("Provider result contains no usable observations")
    return CanonicalResult(
        job_id=raw.job_id,
        source_provider_result_hash=hash_config(raw.model_dump(mode="json")),
        measurement_mapping_hash=hash_config(mapping.model_dump(mode="json")),
        canonical_counts=dict(sorted(canonical_counts.items())),
        canonical_shots=canonical_shots,
        canonicalized_shots=sum(canonical_counts.values()),
        all_outputs_length_98=all(len(value) == 98 for value in canonical_counts),
        package_versions=package_versions(),
    )


def _layout_signature(layout: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [
        (
            register.get("name"),
            register.get("provider_order"),
            register.get("provider_bit_order"),
            tuple(register.get("bit_indices", [])),
            tuple(register.get("classical_indices", [])),
        )
        for register in layout
    ]


def _layout_from_bits(bits: list[Any]) -> list[dict[str, Any]]:
    registers: dict[str, list[tuple[int, int]]] = {}
    order: list[str] = []
    for global_index, bit in enumerate(bits):
        name = str(bit.reg_name)
        if name not in registers:
            registers[name] = []
            order.append(name)
        if len(bit.index) != 1:
            raise ValueError(f"Provider bit is not one-dimensionally indexable: {bit}")
        registers[name].append((int(bit.index[0]), global_index))
    return [
        {
            "name": name,
            "provider_order": provider_order,
            "provider_bit_order": "lsb_left",
            "bit_indices": [local for local, _ in registers[name]],
            "classical_indices": [global_index for _, global_index in registers[name]],
            "ordering_source": "BackendResult.get_bitlist and explicit get_counts(cbits=bitlist)",
        }
        for provider_order, name in enumerate(order)
    ]


def retrieve_existing_quantinuum_job(job_id: str, device_name: str) -> ProviderRawResult:
    """Retrieve only; this function has no call to process_circuit(s)."""
    backend_module = importlib.import_module("pytket.extensions.quantinuum")
    backend = backend_module.QuantinuumBackend(device_name=device_name)
    result_module = importlib.import_module("pytket.backends")
    try:
        handle = result_module.ResultHandle.from_str(job_id)
    except Exception:
        handle = result_module.ResultHandle(job_id)
    result = backend.get_result(handle)
    bits = result.get_bitlist()
    counts = {
        "".join(str(bit) for bit in outcome): int(count)
        for outcome, count in result.get_counts(cbits=bits).items()
    }
    try:
        shot_array = result.get_shots(cbits=bits)
        shots = [[int(bit) for bit in row] for row in shot_array.tolist()]
    except Exception:
        shots = []
    returned = sum(counts.values())
    return ProviderRawResult(
        device_name=device_name,
        job_id=job_id,
        requested_shots=returned,
        returned_shots=returned,
        raw_counts=counts,
        raw_shots=shots,
        raw_register_layout=_layout_from_bits(bits),
        raw_result_order="lsb_left",
        package_versions=package_versions(),
    )


def persist_imported_result(
    root: Path,
    raw: ProviderRawResult,
    mapping: MeasurementMapping,
    *,
    bootstrap_replicates: int = 100,
    seed: int = 12345,
) -> dict[str, Path]:
    canonical = normalize_provider_result(raw, mapping)
    safe_job_id = re.sub(r"[^A-Za-z0-9_.-]", "_", raw.job_id)
    raw_path = root / "data/provider_raw" / f"{safe_job_id}.json"
    counts_path = root / "data/canonical" / f"{safe_job_id}.counts.json"
    shots_path = root / "data/canonical" / f"{safe_job_id}.shots.jsonl"
    job_dir = root / "results/jobs" / safe_job_id
    write_json(raw_path, raw)
    write_aggregated_counts(
        counts_path,
        canonical.canonical_counts,
        bit_order="canonical",
        metadata={
            "job_id": raw.job_id,
            "source_provider_result_hash": canonical.source_provider_result_hash,
            "measurement_mapping_hash": canonical.measurement_mapping_hash,
        },
    )
    if raw.raw_shots:
        write_shots_jsonl(
            shots_path,
            zip(
                (provider_value_to_raw_string(value) for value in raw.raw_shots),
                canonical.canonical_shots,
                strict=True,
            ),
        )
    metadata = ProviderJobMetadata(
        device_name=raw.device_name,
        job_id=raw.job_id,
        job_label=raw.job_label,
        submitted_circuit_hash=raw.submitted_circuit_hash,
        requested_shots=raw.requested_shots,
        returned_shots=raw.returned_shots,
        job_status=raw.job_status,
        queue_time_seconds=raw.queue_time_seconds,
        execution_time_seconds=raw.execution_time_seconds,
        reported_cost_hqcs=raw.reported_cost_hqcs,
        provider_metadata={"calibration_metadata": raw.calibration_metadata},
        package_versions=package_versions(),
    )
    write_json(job_dir / "job_metadata.json", metadata)
    write_json(job_dir / "normalization_report.json", canonical)
    counts = canonical.canonical_counts
    methods = [
        most_frequent_string,
        bitwise_majority_string,
        weighted_observed_medoid,
        cluster_consensus,
    ]
    candidates = [method(counts) for method in methods]
    recovery = RecoveryReport(
        candidates=candidates,
        method_agreement=method_agreement(candidates),
        package_versions=package_versions(),
        input_hashes={counts_path.relative_to(root).as_posix(): sha256_file(counts_path)},
        random_seed=seed,
    )
    write_json(job_dir / "recovery_report.json", recovery)
    bootstraps: list[BootstrapReport] = [
        bootstrap_recovery(counts, method, replicates=bootstrap_replicates, seed=seed + index)
        for index, method in enumerate(methods)
    ]
    write_json(
        job_dir / "bootstrap_report.json", [item.model_dump(mode="json") for item in bootstraps]
    )
    return {
        "raw": raw_path,
        "counts": counts_path,
        "shots": shots_path,
        "metadata": job_dir / "job_metadata.json",
        "normalization": job_dir / "normalization_report.json",
        "recovery": job_dir / "recovery_report.json",
        "bootstrap": job_dir / "bootstrap_report.json",
    }
