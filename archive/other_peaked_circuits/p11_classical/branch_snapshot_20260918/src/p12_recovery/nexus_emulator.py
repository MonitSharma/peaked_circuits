from __future__ import annotations

import importlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .bootstrap import bootstrap_recovery, prefix_shot_scaling
from .counts_io import write_aggregated_counts, write_shots_jsonl
from .hashing import sha256_bytes, sha256_file
from .mapping_validation import validation_patterns
from .models import (
    EmulatorMappingAggregateReport,
    P12EmulatorPilotReport,
    ProviderOutputMappingReport,
    QIRExportReport,
    QIRMappingCasesReport,
    RawProviderResultReport,
)
from .nexus_results import ParsedProviderResult, parse_provider_result, validate_result_shape
from .nexus_syntax_check import MAPPING_CASE_ORDER
from .provider_mapping import (
    infer_labeled_qir_mapping,
    majority_by_field,
    qir_declared_result_layout,
)
from .recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)
from .reporting import package_versions, write_json


def _safe_ref(value: Any) -> str:
    identifier = getattr(value, "id", None)
    return str(identifier if identifier is not None else value)


def _safe_status(value: Any) -> str:
    status = getattr(value, "status", value)
    return str(getattr(status, "value", status))


def _raw_payload(result: Any) -> Any:
    payload = getattr(result, "results", None)
    if isinstance(payload, str):
        return payload
    model_dump = getattr(result, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(result, (dict, list, str, int, float, bool)) or result is None:
        return result
    return {"type": type(result).__name__, "representation": str(result)}


def _payload_bytes(payload: Any) -> bytes:
    if isinstance(payload, str):
        return payload.encode()
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def execute_mapping_cases(
    root: Path,
    *,
    target: str,
    shots: int,
    max_cost: float,
    case_filter: str | None = None,
    minimum_majority_fraction: float = 0.67,
    project_name: str = "p12-helios-recovery",
    timeout_seconds: float = 1800,
    client_module: Any | None = None,
) -> EmulatorMappingAggregateReport:
    """Execute frozen cases sequentially on Helios-1E; caller must run the guard first."""
    if target != "Helios-1E":
        raise ValueError("Emulator execution is restricted to Helios-1E")
    if shots <= 0 or max_cost <= 0:
        raise ValueError("Positive shots and max_cost are required")
    qnx = client_module or importlib.import_module("qnexus")
    project = qnx.projects.get_or_create(
        name=project_name,
        description="Cost-capped deterministic P12 output mapping on Helios-1E",
    )
    mapping_report = QIRMappingCasesReport.model_validate_json(
        (root / "results/qir/mapping_cases/mapping_qir_export_report.json").read_text()
    )
    cases = {case.case_name: case for case in mapping_report.cases}
    selected = [case_filter] if case_filter else MAPPING_CASE_ORDER
    if any(name not in cases for name in selected):
        raise ValueError("Unknown mapping case")
    parsed_cases: dict[str, ParsedProviderResult] = {}
    statuses: dict[str, Any] = {}
    expected = validation_patterns()
    for case_name in selected:
        case = cases[case_name]
        export = QIRExportReport.model_validate_json((root / case.export_report_path).read_text())
        bitcode_path = root / export.qir_bitcode_path
        if sha256_file(bitcode_path) != export.qir_bitcode_sha256:
            statuses[case_name] = {"status": "failed", "stage": "artifact_hash"}
            break
        existing_case_path = (
            root / "results/nexus/emulator_mapping" / case_name / "mapping_report.json"
        )
        existing_raw_path = root / "data/provider_raw/mapping" / case_name / "raw_payload.json"
        if case_filter is None and existing_case_path.is_file() and existing_raw_path.is_file():
            import json

            existing_case = json.loads(existing_case_path.read_text())
            existing_raw = RawProviderResultReport.model_validate_json(
                existing_raw_path.read_text()
            )
            if (
                existing_case.get("status") == "passed"
                and existing_case.get("shots") == shots
                and existing_case.get("max_cost") == max_cost
                and existing_case.get("bitcode_sha256") == export.qir_bitcode_sha256
                and sha256_bytes(_payload_bytes(existing_raw.raw_payload))
                == existing_raw.raw_payload_sha256
            ):
                parsed_cases[case_name] = parse_provider_result(existing_raw.raw_payload)
                statuses[case_name] = {**existing_case, "reused_audited_result": True}
                continue
        try:
            qir_ref = qnx.qir.upload(
                qir=bitcode_path.read_bytes(),
                name=f"mapping-{case_name}-{export.qir_bitcode_sha256[:12]}",
                project=project,
                description="Frozen deterministic mapping case for Helios-1E",
            )
            # Helios emulators require an explicit Selene configuration. MPS supports
            # this 98-qubit, zero-entanglement mapping workload; NoErrorModel makes the
            # output-layout experiment deterministic instead of a fidelity experiment.
            config = qnx.models.HeliosConfig(
                system_name="Helios-1E",
                emulator_config=qnx.models.HeliosEmulatorConfig(
                    n_qubits=98,
                    simulator=qnx.models.MatrixProductStateSimulator(),
                    error_model=qnx.models.NoErrorModel(),
                ),
            )
            submitted = datetime.now(UTC)
            job_ref = qnx.start_execute_job(
                programs=[qir_ref],
                n_shots=[shots],
                max_cost=[max_cost],
                n_qubits=[98],
                backend_config=config,
                project=project,
                name=f"p12-mapping-{case_name}-{submitted:%Y%m%dT%H%M%S}",
                description="Cost-capped mapping validation; physical Helios-1 forbidden",
            )
            terminal = qnx.jobs.wait_for(job_ref, timeout=timeout_seconds)
            final_status = _safe_status(terminal)
            if final_status.upper() != "COMPLETED":
                raise RuntimeError(f"Nexus terminal status: {final_status}")
            result_refs = list(qnx.jobs.results(job_ref))
            if len(result_refs) != 1:
                raise RuntimeError(f"Expected one result reference, received {len(result_refs)}")
            result_ref = result_refs[0]
            result = result_ref.download_result()
            payload = _raw_payload(result)
            payload_hash = sha256_bytes(_payload_bytes(payload))
            parsed = parse_provider_result(result)
            validate_result_shape(parsed)
            majority, fractions, inconsistent = majority_by_field(
                parsed, minimum_majority_fraction=minimum_majority_fraction
            )
            canonical = ["?"] * 98
            for field, bit in majority.items():
                if not (field.startswith("m") and field.endswith("[0]") and field[1:4].isdigit()):
                    raise ValueError(f"Unrecognized labeled QIR field: {field}")
                canonical[int(field[1:4])] = str(bit)
            canonical_string = "".join(canonical)
            if canonical_string != expected[case_name]:
                raise ValueError("Deterministic canonical output does not match expected pattern")
            raw_dir = root / "data/provider_raw/mapping" / case_name
            report_dir = root / "results/nexus/emulator_mapping" / case_name
            job_data = {
                "project_ref": _safe_ref(project),
                "qir_artifact_ref": _safe_ref(qir_ref),
                "job_ref": _safe_ref(job_ref),
                "target": target,
                "submitted_at": submitted.isoformat(),
                "final_status": final_status,
                "shots": shots,
                "max_cost": max_cost,
                "bitcode_sha256": export.qir_bitcode_sha256,
            }
            write_json(raw_dir / "job.json", job_data)
            write_json(raw_dir / "result.json", {"result_ref": _safe_ref(result_ref)})
            raw_report = RawProviderResultReport(
                target=target,
                case_name=case_name,
                job_ref=_safe_ref(job_ref),
                result_ref=_safe_ref(result_ref),
                result_type=type(result).__name__,
                raw_payload=payload,
                raw_payload_sha256=payload_hash,
                requested_shots=shots,
                returned_shots=parsed.shot_count,
                reported_cost_hqcs=(
                    float(result_ref.cost)
                    if getattr(result_ref, "cost", None) is not None
                    else None
                ),
                package_versions=package_versions(),
                input_hashes={export.qir_bitcode_path: export.qir_bitcode_sha256},
            )
            write_json(raw_dir / "raw_payload.json", raw_report)
            normalization = {
                "status": "passed",
                "output_width": 98,
                "shots_requested": shots,
                "shots_returned": parsed.shot_count,
                "canonical_output": canonical_string,
                "expected_output": expected[case_name],
                "minimum_majority_fraction": min(fractions.values()),
                "inconsistent_fields": inconsistent,
                "provider_structure": parsed.as_dict(),
            }
            write_json(report_dir / "normalization_report.json", normalization)
            case_report = {
                **job_data,
                **normalization,
                "reported_cost_hqcs": raw_report.reported_cost_hqcs,
                "raw_payload_sha256": payload_hash,
            }
            write_json(report_dir / "mapping_report.json", case_report)
            (report_dir / "mapping_report.md").write_text(
                f"# Mapping case `{case_name}`\n\nStatus: **passed**  \n"
                f"Job: `{_safe_ref(job_ref)}`  \nShots: `{shots}`  \nOutput width: `98`  \n"
                f"Reported cost: `{raw_report.reported_cost_hqcs}` HQC\n"
            )
            parsed_cases[case_name] = parsed
            statuses[case_name] = case_report
        except Exception as exc:
            statuses[case_name] = {
                "status": "failed",
                "stage": "execution_or_result_normalization",
                "diagnostic": f"{type(exc).__name__}: {exc}",
                "stopped_before_remaining_cases": True,
            }
            break
    complete = case_filter is None and len(parsed_cases) == len(MAPPING_CASE_ORDER)
    resolved = 0
    if complete:
        declared_layouts = {
            name: qir_declared_result_layout(root / cases[name].qir_path)
            for name in MAPPING_CASE_ORDER
        }
        p12_layout = qir_declared_result_layout(root / "results/qir/p12.ll")
        inferred = infer_labeled_qir_mapping(
            parsed_cases,
            expected,
            minimum_majority_fraction=minimum_majority_fraction,
            expected_provider_layouts=declared_layouts,
            output_mapping_layout=p12_layout,
        )
        mapping = ProviderOutputMappingReport(
            **{
                key: value
                for key, value in inferred.items()
                if key not in {"parser_values", "raw_value_count"}
            },
            package_versions=package_versions(),
        )
        write_json(root / "results/nexus/emulator_mapping/provider_output_mapping.json", mapping)
        (root / "results/nexus/emulator_mapping/provider_output_mapping.md").write_text(
            "# Verified Nexus provider-output mapping\n\n"
            "All 98 labeled QIR result positions were uniquely resolved and validated across "
            "six deterministic, reversal-sensitive Helios-1E cases.\n"
        )
        resolved = 98
    passed = complete and resolved == 98
    aggregate = EmulatorMappingAggregateReport(
        status="passed" if passed else ("incomplete" if case_filter else "failed"),
        target=target,
        ordered_cases=MAPPING_CASE_ORDER,
        case_statuses=statuses,
        provider_result_order_verified=passed,
        emulator_mapping_validation_passed=passed,
        resolved_positions=resolved,
        unresolved_positions=98 - resolved,
        max_cost_per_job=max_cost,
        shots_per_case=shots,
        package_versions=package_versions(),
    )
    write_json(root / "results/nexus/emulator_mapping/emulator_mapping_report.json", aggregate)
    return aggregate


def execute_p12_pilot(
    root: Path,
    *,
    target: str,
    shots: int,
    max_cost: float,
    project_name: str = "p12-helios-recovery",
    timeout_seconds: float = 1800,
    client_module: Any | None = None,
) -> P12EmulatorPilotReport:
    """Run at most 20 blinded P12 shots after the external emulator guard passes."""
    if target != "Helios-1E" or not 0 < shots <= 20 or max_cost <= 0:
        raise ValueError("P12 pilot requires Helios-1E, 1..20 shots, and positive max_cost")
    qnx = client_module or importlib.import_module("qnexus")
    export = QIRExportReport.model_validate_json(
        (root / "results/qir/qir_export_report.json").read_text()
    )
    bitcode_path = root / export.qir_bitcode_path
    if sha256_file(bitcode_path) != export.qir_bitcode_sha256:
        raise RuntimeError("Frozen P12 bitcode hash mismatch")
    project = qnx.projects.get_or_create(
        name=project_name, description="Blinded, cost-capped P12 Helios-1E pilot"
    )
    qir_ref = qnx.qir.upload(
        qir=bitcode_path.read_bytes(),
        name=f"p12-pilot-{export.qir_bitcode_sha256[:12]}",
        project=project,
        description="At-most-20-shot blinded emulator pipeline pilot",
    )
    simulator = qnx.models.MatrixProductStateSimulator(
        backend="auto",
        chi=128,
        zero_threshold=0.01,
    )
    simulator_configuration = {
        "type": "MatrixProductStateSimulator",
        "backend": "auto",
        "chi": 128,
        "zero_threshold": 0.01,
        "precision": 32,
        "approximation_warning": (
            "Bounded-MPS pilot configuration; suitable for pipeline validation only, "
            "not fidelity or accuracy claims."
        ),
    }
    config = qnx.models.HeliosConfig(
        system_name="Helios-1E",
        emulator_config=qnx.models.HeliosEmulatorConfig(
            n_qubits=98,
            simulator=simulator,
            error_model=qnx.models.NoErrorModel(),
        ),
    )
    job_ref = qnx.start_execute_job(
        programs=[qir_ref],
        n_shots=[shots],
        n_qubits=[98],
        max_cost=[max_cost],
        backend_config=config,
        project=project,
        name=f"p12-pilot-{datetime.now(UTC):%Y%m%dT%H%M%S}",
        description="Blinded P12 pipeline validation; never score hidden target",
    )
    job_id = _safe_ref(job_ref)
    raw_dir = root / "data/provider_raw/p12_emulator" / job_id
    canonical_dir = root / "data/canonical/p12_emulator" / job_id
    result_dir = root / "results/nexus/p12_emulator" / job_id
    job_metadata = {
        "project_ref": _safe_ref(project),
        "qir_artifact_ref": _safe_ref(qir_ref),
        "job_ref": job_id,
        "target": target,
        "shots": shots,
        "max_cost": max_cost,
        "bitcode_sha256": export.qir_bitcode_sha256,
        "simulator_configuration": simulator_configuration,
        "hidden_target_scored": False,
    }
    write_json(raw_dir / "job.json", job_metadata)
    write_json(result_dir / "job_metadata.json", job_metadata)
    try:
        terminal = qnx.jobs.wait_for(job_ref, timeout=timeout_seconds)
        final_status = _safe_status(terminal)
        if final_status.upper() != "COMPLETED":
            raise RuntimeError(f"Nexus terminal status: {final_status}")
        refs = list(qnx.jobs.results(job_ref))
        if len(refs) != 1:
            raise RuntimeError("P12 pilot expected exactly one result")
        result_ref = refs[0]
        result = result_ref.download_result()
        parsed = parse_provider_result(result)
        validate_result_shape(parsed)
    except Exception as exc:
        try:
            status = qnx.jobs.status(job_ref)
        except Exception:
            status = None
        final_status = _safe_status(status) if status is not None else "ERROR"
        reported_cost = getattr(status, "cost", None) if status is not None else None
        provider_detail = getattr(status, "error_detail", None) if status is not None else None
        diagnostic = str(provider_detail or exc)
        failure = P12EmulatorPilotReport(
            status="failed",
            target=target,
            shots=shots,
            max_cost=max_cost,
            job_ref=job_id,
            final_status=final_status,
            failure_stage="job_wait_or_result_retrieval",
            diagnostics=[diagnostic],
            simulator_configuration=simulator_configuration,
            reported_cost_hqcs=(float(reported_cost) if reported_cost is not None else None),
            package_versions=package_versions(),
            input_hashes={export.qir_bitcode_path: export.qir_bitcode_sha256},
        )
        write_json(result_dir / "pilot_report.json", failure)
        write_json(root / "results/nexus/p12_emulator/pilot_report.json", failure)
        (result_dir / "diagnostics.txt").write_text(diagnostic + "\n")
        (result_dir / "pilot_report.md").write_text(
            "# Blinded P12 emulator pilot\n\n"
            f"Status: **failed**  \nJob: `{job_id}`  \nStage: `job_wait_or_result_retrieval`  \n"
            f"Reported cost: `{failure.reported_cost_hqcs}` HQC\n\n"
            "No provider measurements were normalized and the hidden target was not scored.\n"
        )
        return failure
    by_shot: dict[int, dict[str, int]] = {}
    for value in parsed.values:
        by_shot.setdefault(value.shot_index, {})[value.provider_name] = value.bit_value
    canonical_shots = [
        "".join(str(by_shot[shot][f"m{index:03d}[0]"]) for index in range(98))
        for shot in sorted(by_shot)
    ]
    counts = dict(Counter(canonical_shots))
    payload = _raw_payload(result)
    write_json(
        raw_dir / "raw_payload.json",
        {
            "raw_payload": payload,
            "raw_payload_sha256": sha256_bytes(_payload_bytes(payload)),
            "result_ref": _safe_ref(result_ref),
        },
    )
    write_aggregated_counts(
        canonical_dir / "counts.json", counts, metadata={"job_ref": job_id, "blinded": True}
    )
    write_shots_jsonl(canonical_dir / "shots.jsonl", ((shot, shot) for shot in canonical_shots))
    methods = [
        most_frequent_string,
        bitwise_majority_string,
        weighted_observed_medoid,
        cluster_consensus,
    ]
    candidates = [method(counts) for method in methods]
    recovery = {
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        "method_agreement": method_agreement(candidates),
        "pairwise_hamming_distances": [
            sum(
                a != b
                for a, b in zip(left.canonical_bitstring, right.canonical_bitstring, strict=True)
            )
            for index, left in enumerate(candidates)
            for right in candidates[index + 1 :]
        ],
        "shot_prefix_stability": prefix_shot_scaling(
            canonical_shots, bitwise_majority_string, list(range(1, shots + 1))
        ),
        "hidden_target_scored": False,
    }
    write_json(result_dir / "normalization_report.json", {"status": "passed", "width": 98})
    write_json(result_dir / "recovery_report.json", recovery)
    write_json(
        result_dir / "bootstrap_report.json",
        bootstrap_recovery(counts, bitwise_majority_string, replicates=100, seed=12345),
    )
    pilot = P12EmulatorPilotReport(
        status="passed",
        target=target,
        shots=shots,
        max_cost=max_cost,
        job_ref=job_id,
        final_status=final_status,
        simulator_configuration=simulator_configuration,
        reported_cost_hqcs=(
            float(result_ref.cost) if getattr(result_ref, "cost", None) is not None else None
        ),
        normalized_width=98,
        package_versions=package_versions(),
        input_hashes={export.qir_bitcode_path: export.qir_bitcode_sha256},
    )
    write_json(result_dir / "pilot_report.json", pilot)
    write_json(root / "results/nexus/p12_emulator/pilot_report.json", pilot)
    (result_dir / "pilot_report.md").write_text(
        "# Blinded P12 emulator pilot\n\nPipeline normalization passed. The hidden target was not scored.\n"
    )
    return pilot
