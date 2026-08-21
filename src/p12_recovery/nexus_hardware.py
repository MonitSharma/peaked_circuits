"""Fail-closed, resumable physical Helios-1 campaign boundary.

This module contains the future execution surface, but this Milestone never calls
the submission function. All integration tests use a fake Nexus client.
"""

from __future__ import annotations

import importlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .campaign import BatchStatus, CampaignState, CampaignStore
from .constants import HARDWARE_CONFIRMATION, P12_QUBITS
from .hashing import sha256_file


class PhysicalSubmissionDisabled(PermissionError):
    """Raised whenever a physical submission is not fully authorized."""


class HardwarePreflightReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    batch_id: str
    target: str
    requested_shots: int
    predicted_hqc: float | None
    recommended_max_cost: float | None
    monthly_budget_hqc: float = 3000
    user_spend_ceiling_hqc: float = 1500
    checks: dict[str, bool]
    blockers: list[str] = Field(default_factory=list)
    authorization_checks: dict[str, bool] = Field(
        default_factory=lambda: {
            "environment_authorized": False,
            "cli_authorized": False,
            "typed_confirmation": False,
        }
    )
    hardware_submission_authorized_by_user: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def passed(self) -> bool:
        return not self.blockers and all(self.checks.values())

    @property
    def structural_passed(self) -> bool:
        return not self.blockers and all(self.checks.values())


class HardwarePreflight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    target_type: str
    qubit_capacity: int
    source_qasm_sha256: str
    qir_sha256: str
    bitcode_sha256: str
    syntax_check_passed: bool
    mapping_verified: bool
    predicted_hqc: float
    requested_shots: int
    max_cost: float
    protocol_frozen: bool
    campaign_valid: bool
    no_active_job: bool
    explicit_environment_authorized: bool = False
    explicit_cli_authorized: bool = False
    typed_confirmation: bool = False
    user_spend_ceiling_hqc: float = 1500

    @property
    def structural_passed(self) -> bool:
        return all(
            (
                self.target == "Helios-1",
                self.target_type == "hardware",
                self.qubit_capacity >= P12_QUBITS,
                len(self.source_qasm_sha256) == 64,
                len(self.qir_sha256) == 64,
                len(self.bitcode_sha256) == 64,
                self.syntax_check_passed,
                self.mapping_verified,
                self.predicted_hqc > 0,
                self.requested_shots > 0,
                self.max_cost > 0,
                self.max_cost <= min(3000, self.user_spend_ceiling_hqc),
                self.max_cost >= self.predicted_hqc,
                self.protocol_frozen,
                self.campaign_valid,
                self.no_active_job,
            )
        )


def assert_hardware_preflight(preflight: HardwarePreflight) -> None:
    checks = {
        "exact_target": preflight.target == "Helios-1",
        "hardware_target": preflight.target_type == "hardware",
        "98_qubit_capacity": preflight.qubit_capacity >= P12_QUBITS,
        "source_hash": len(preflight.source_qasm_sha256) == 64,
        "qir_hash": len(preflight.qir_sha256) == 64,
        "bitcode_hash": len(preflight.bitcode_sha256) == 64,
        "syntax_check": preflight.syntax_check_passed,
        "provider_mapping": preflight.mapping_verified,
        "fresh_cost": preflight.predicted_hqc > 0,
        "shots_within_cost": preflight.predicted_hqc < min(3000, preflight.user_spend_ceiling_hqc),
        "shots_positive": preflight.requested_shots > 0,
        "max_cost_positive": preflight.max_cost > 0,
        "max_cost_within_budget": preflight.max_cost <= min(3000, preflight.user_spend_ceiling_hqc),
        "max_cost_covers_prediction": preflight.max_cost >= preflight.predicted_hqc,
        "protocol_frozen": preflight.protocol_frozen,
        "campaign_valid": preflight.campaign_valid,
        "no_active_job": preflight.no_active_job,
        "environment_authorized": preflight.explicit_environment_authorized,
        "cli_authorized": preflight.explicit_cli_authorized,
        "typed_confirmation": preflight.typed_confirmation,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise PhysicalSubmissionDisabled("Physical submission blocked: " + ", ".join(failed))


def build_preflight_report(root: Path, state: CampaignState, batch_id: str, *, discovery: dict[str, Any], predicted_hqc: float | None, max_cost: float | None) -> HardwarePreflightReport:
    batch = state.batches.get(batch_id)
    if batch is None:
        raise KeyError(batch_id)
    target: dict[str, Any] = next((item for item in discovery.get("devices", []) if item.get("device_name") == "Helios-1"), {})
    syntax = _load(root / "results/nexus/syntax_check/p12/syntax_check_report.json")
    mapping = _load(root / "results/nexus/emulator_mapping/provider_output_mapping.json")
    qir_export = _load(root / "results/qir/qir_export_report.json")
    cost_report = _load(root / "results/nexus/cost/p12_cost.json")
    cost_item = next((item for item in cost_report.get("items", []) if item.get("program_name") == "p12" and item.get("shots") == batch.requested_shots), None)
    cost_timestamp = _parse_timestamp(cost_item.get("provider_timestamp")) if cost_item else None
    cost_fresh = cost_timestamp is not None and (datetime.now(UTC) - cost_timestamp).total_seconds() <= 24 * 3600
    checks = {
        "exact_target": target.get("device_name") == "Helios-1",
        "hardware_target": target.get("target_type") == "hardware",
        "98_qubit_capacity": int(target.get("qubit_capacity") or 0) >= 98,
        "source_hash": state.source_qasm_sha256 == qir_export.get("source_qasm_sha256"),
        "qir_hash": state.qir_sha256 == qir_export.get("qir_sha256") and sha256_file(root / "results/qir/p12.ll") == state.qir_sha256,
        "bitcode_hash": state.qir_bitcode_sha256 == qir_export.get("qir_bitcode_sha256") and sha256_file(root / "results/qir/p12.bc") == state.qir_bitcode_sha256,
        "syntax_check": syntax.get("status") == "passed" and syntax.get("target") == "Helios-1SC",
        "provider_mapping": mapping.get("provider_result_order_verified") is True and mapping.get("resolved_positions") == 98,
        "fresh_cost": predicted_hqc is not None and predicted_hqc > 0 and cost_fresh and (cost_item or {}).get("bitcode_sha256") == state.qir_bitcode_sha256,
        "shots_within_cost": predicted_hqc is not None and predicted_hqc < min(state.monthly_hqc_budget, state.user_spend_ceiling_hqc),
        "shots_positive": batch.requested_shots > 0,
        "max_cost_positive": max_cost is not None and max_cost > 0,
        "max_cost_within_budget": max_cost is not None and max_cost <= min(state.monthly_hqc_budget, state.user_spend_ceiling_hqc),
        "max_cost_covers_prediction": max_cost is not None and predicted_hqc is not None and max_cost >= predicted_hqc,
        "protocol_frozen": state.protocol_version == "3.0" and state.protocol_hash is not None,
        "campaign_valid": not state.external_target_scored,
        "no_active_job": state.active_job is None,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return HardwarePreflightReport(
        batch_id=batch_id,
        target=target.get("device_name", "missing"),
        requested_shots=batch.requested_shots,
        predicted_hqc=predicted_hqc,
        recommended_max_cost=max_cost,
        user_spend_ceiling_hqc=state.user_spend_ceiling_hqc,
        checks=checks,
        blockers=blockers,
    )


def dry_run_hardware_batch(root: Path, preflight: HardwarePreflightReport, *, project_name: str = "p12-helios-recovery", job_name: str | None = None) -> dict[str, Any]:
    """Render intended provider parameters; deliberately makes no provider call."""
    return {
        "dry_run": True,
        "provider_call_made": False,
        "target": "Helios-1",
        "shots": preflight.requested_shots,
        "max_cost": preflight.recommended_max_cost,
        "batch_id": preflight.batch_id,
        "project_name": project_name,
        "job_name": job_name or f"p12-physical-{preflight.batch_id}",
        "hardware_submission_authorized_by_user": False,
        "blockers": preflight.blockers,
    }


def submit_hardware_batch(root: Path, state: CampaignState, batch_id: str, *, preflight: HardwarePreflight, execute_hardware: bool = False, environment: dict[str, str] | None = None, interactive_confirmed: bool = False, client_module: Any | None = None) -> dict[str, str]:
    """Submit exactly once; a pending batch always requires explicit reconciliation."""
    store = CampaignStore(root)
    batch = state.batches.get(batch_id)
    if batch is None:
        raise KeyError(batch_id)
    if state.active_job is not None or batch.execution_job_ref or batch.status in {BatchStatus.SUBMISSION_PENDING, BatchStatus.SUBMITTED, BatchStatus.RUNNING, BatchStatus.COMPLETED}:
        raise PhysicalSubmissionDisabled("Batch already has a submitted/active job; use hardware-status or hardware-retrieve")
    env = environment or os.environ
    armed = preflight.model_copy(update={"explicit_environment_authorized": env.get("P12_ENABLE_PHYSICAL_HELIOS") == "1", "explicit_cli_authorized": execute_hardware, "typed_confirmation": interactive_confirmed})
    assert_hardware_preflight(armed)
    if env.get("P12_CONFIRM_PAID_EXECUTION") != HARDWARE_CONFIRMATION:
        raise PhysicalSubmissionDisabled("Paid-execution confirmation phrase is missing")
    if not preflight.structural_passed:
        raise PhysicalSubmissionDisabled("Structural hardware preflight has not passed")
    qnx = client_module or importlib.import_module("qnexus")
    job_name = f"p12-physical-{batch_id}-{state.qir_bitcode_sha256[:8]}-{(state.protocol_hash or '')[:8]}"
    CampaignStore(root).update_batch(state, batch_id, status=BatchStatus.SUBMISSION_PENDING, provider_job_name=job_name)
    project = qnx.projects.get_or_create(name="p12-helios-recovery", description="P12 physical campaign")
    artifact = qnx.qir.upload(qir=(root / "results/qir/p12.bc").read_bytes(), name=job_name, project=project, description="Frozen P12 QIR for explicitly authorized hardware")
    job = qnx.start_execute_job(programs=[artifact], n_shots=[batch.requested_shots], backend_config=qnx.models.HeliosConfig(system_name="Helios-1"), project=project, name=job_name, max_cost=batch.max_cost)
    project_ref = str(getattr(project, "id", project))
    artifact_ref = str(getattr(artifact, "id", artifact))
    job_ref = str(getattr(job, "id", job))
    store.update_batch(state, batch_id, status=BatchStatus.SUBMITTED, nexus_project_ref=project_ref, qir_artifact_ref=artifact_ref, execution_job_ref=job_ref, submission_timestamp=datetime.now(UTC))
    return {"project_ref": project_ref, "qir_artifact_ref": artifact_ref, "job_ref": job_ref, "job_name": job_name}


def poll_hardware_batch(root: Path, state: CampaignState, batch_id: str, *, client_module: Any | None = None) -> dict[str, Any]:
    batch = state.batches.get(batch_id)
    if batch is None or not batch.execution_job_ref:
        raise ValueError("No saved hardware job exists for this batch")
    qnx = client_module or importlib.import_module("qnexus")
    job_ref = qnx.jobs.get(id=batch.execution_job_ref)
    status = qnx.jobs.status(job_ref)
    status_text = str(getattr(status, "value", getattr(status, "status", status)))
    CampaignStore(root).update_batch(state, batch_id, status=_status_from_provider(status_text))
    return {"batch_id": batch_id, "job_ref": batch.execution_job_ref, "status": status_text}


def reconcile_hardware_batch(root: Path, state: CampaignState, batch_id: str, *, client_module: Any | None = None) -> str:
    """Resolve a pending submission by deterministic provider job name only."""
    batch = state.batches.get(batch_id)
    if batch is None or batch.status != BatchStatus.SUBMISSION_PENDING or not batch.provider_job_name:
        raise PhysicalSubmissionDisabled("Only a SUBMISSION_PENDING batch can be reconciled")
    qnx = client_module or importlib.import_module("qnexus")
    try:
        job_ref = qnx.jobs.get(name=batch.provider_job_name)
    except Exception as exc:
        raise PhysicalSubmissionDisabled("No matching Nexus job found; explicit recovery action is required") from exc
    if isinstance(job_ref, (list, tuple)):
        if len(job_ref) != 1:
            raise PhysicalSubmissionDisabled("Nexus reconciliation is ambiguous; refusing to attach or resubmit")
        job_ref = job_ref[0]
    job_id = str(getattr(job_ref, "id", job_ref))
    CampaignStore(root).update_batch(state, batch_id, status=BatchStatus.SUBMITTED, execution_job_ref=job_id)
    return job_id


def retrieve_hardware_batch(root: Path, state: CampaignState, batch_id: str, *, client_module: Any | None = None) -> Path:
    batch = state.batches.get(batch_id)
    if batch is None or not batch.execution_job_ref:
        raise ValueError("No saved hardware job exists for this batch")
    qnx = client_module or importlib.import_module("qnexus")
    job_ref = qnx.jobs.get(id=batch.execution_job_ref)
    results = list(qnx.jobs.results(job_ref, allow_incomplete=False))
    directory = root / "hardware_campaign" / batch_id / "provider"
    directory.mkdir(parents=True, exist_ok=True)
    refs = [str(getattr(item, "id", item)) for item in results]
    job_payload = _jsonable(job_ref)
    (directory / "job.json").write_text(json.dumps(job_payload, indent=2, sort_keys=True) + "\n")
    (directory / "result_ref.json").write_text(json.dumps(refs, indent=2) + "\n")
    first = results[0] if results else None
    _download_artifact(first, "raw_result.json", directory, "download_result")
    _download_artifact(first, "backend_info.json", directory, "download_backend_info")
    _download_artifact(first, "submitted_input.bc", directory, "get_input", binary=True)
    manifest = {"job_ref": batch.execution_job_ref, "result_refs": refs, "returned_shots": _returned_shots(first), "reported_cost_hqcs": _cost(first, job_ref)}
    (directory / "provider_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    sums = []
    for path in sorted(directory.iterdir()):
        if path.name != "SHA256SUMS" and path.is_file():
            sums.append(f"{sha256_file(path)}  {path.name}")
    (directory / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    CampaignStore(root).update_batch(state, batch_id, status=BatchStatus.RETRIEVED, result_refs=refs, returned_shots=_returned_shots(first), actual_reported_hqc=_cost(first, job_ref))
    return directory


def _status_from_provider(status: str) -> BatchStatus:
    normalized = status.upper()
    if normalized in {"COMPLETED", "SUCCEEDED", "SUCCESS"}:
        return BatchStatus.COMPLETED
    if normalized in {"FAILED", "ERROR", "CANCELLED"}:
        return BatchStatus.FAILED
    return BatchStatus.RUNNING


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _download_artifact(ref: Any, filename: str, directory: Path, method: str, *, binary: bool = False) -> None:
    if ref is None or not hasattr(ref, method):
        return
    value = getattr(ref, method)()
    path = directory / filename
    if binary and isinstance(value, (bytes, bytearray)):
        path.write_bytes(value)
    elif hasattr(value, "to_json"):
        path.write_text(value.to_json())
    elif isinstance(value, (bytes, bytearray)):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(_jsonable(value), indent=2, sort_keys=True) + "\n")


def _returned_shots(ref: Any) -> int:
    value = getattr(ref, "n_shots", getattr(ref, "shots", 0)) if ref is not None else 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _cost(*refs: Any) -> float | None:
    for ref in refs:
        value = getattr(ref, "cost", getattr(ref, "reported_cost_hqcs", None))
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
