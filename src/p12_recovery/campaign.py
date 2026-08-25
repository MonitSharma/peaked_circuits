"""Persistent, append-safe state for the month-to-month P12 campaign."""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import CIRCUIT_ID
from .hashing import sha256_file


class CampaignStatus(StrEnum):
    PREPARED = "PREPARED"
    HARDWARE_BATCH_ACTIVE = "HARDWARE_BATCH_ACTIVE"
    DISCOVERY_CANDIDATE_FROZEN = "DISCOVERY_CANDIDATE_FROZEN"
    CONFIRMATION_PENDING = "CONFIRMATION_PENDING"
    CAMPAIGN_EVIDENCE_COMPLETE = "CAMPAIGN_EVIDENCE_COMPLETE"


class BatchRole(StrEnum):
    DISCOVERY = "discovery"
    CONFIRMATION = "confirmation"
    ADDITIONAL_REPLICATION = "additional_replication"


class BatchStatus(StrEnum):
    PLANNED = "PLANNED"
    PREFLIGHT_PASSED = "PREFLIGHT_PASSED"
    SUBMISSION_PENDING = "SUBMISSION_PENDING"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    RETRIEVED = "RETRIEVED"
    NORMALIZED = "NORMALIZED"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class BatchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str
    role: BatchRole
    status: BatchStatus = BatchStatus.PLANNED
    source_qasm_sha256: str
    qir_sha256: str
    qir_bitcode_sha256: str
    repository_git_sha: str | None = None
    protocol_hash: str | None = None
    target: str = "Helios-1"
    provider_job_name: str | None = None
    requested_shots: int
    predicted_hqc: float | None = None
    cost_confidence: float | None = None
    max_cost: float | None = None
    actual_reported_hqc: float | None = None
    nexus_project_ref: str | None = None
    qir_artifact_ref: str | None = None
    execution_job_ref: str | None = None
    result_refs: list[str] = Field(default_factory=list)
    submission_timestamp: datetime | None = None
    completion_timestamp: datetime | None = None
    returned_shots: int | None = None
    backend_info_hash: str | None = None
    provider_input_hash: str | None = None
    raw_result_hash: str | None = None
    canonical_result_hash: str | None = None
    analysis_hash: str | None = None
    candidate_freeze_relation: str | None = None
    valid_shots: int = 0
    invalid_shots: int = 0
    failure_reason: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_batch(self) -> BatchRecord:
        if not self.batch_id.startswith("batch_"):
            raise ValueError("Batch IDs must use batch_NNN form")
        if self.requested_shots <= 0:
            raise ValueError("requested_shots must be positive")
        if self.target != "Helios-1":
            raise ValueError("Physical batches are restricted to Helios-1")
        if self.provider_job_name and not (
            self.provider_job_name.startswith("p12-physical-")
            or self.provider_job_name.startswith("p12_physical_")
        ):
            raise ValueError("Provider job names must use a deterministic P12 physical prefix")
        return self


class CampaignState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    campaign_id: str = "p12_physical_campaign_001"
    circuit_id: str = CIRCUIT_ID
    source_qasm_sha256: str
    qir_sha256: str
    qir_bitcode_sha256: str
    protocol_version: str
    protocol_hash: str | None = None
    monthly_hqc_budget: float = 3000
    user_spend_ceiling_hqc: float = 1500
    recommended_shots_per_batch: int | None = 200
    recommended_max_cost: float | None = None
    status: CampaignStatus = CampaignStatus.PREPARED
    next_batch_number: int = 1
    completed_batches: list[str] = Field(default_factory=list)
    batches: dict[str, BatchRecord] = Field(default_factory=dict)
    active_job: dict[str, Any] | None = None
    cumulative_valid_shots: int = 0
    candidate_freeze: dict[str, Any] | None = None
    external_target_scored: bool = False

    @model_validator(mode="after")
    def invariant_checks(self) -> CampaignState:
        if self.circuit_id != CIRCUIT_ID or len(self.source_qasm_sha256) != 64:
            raise ValueError("Campaign identity is not a valid frozen P12 identity")
        if self.external_target_scored:
            raise ValueError("External target scoring is forbidden in this campaign state")
        if self.monthly_hqc_budget != 3000:
            raise ValueError("Monthly campaign budget must remain 3000 HQC")
        if self.user_spend_ceiling_hqc <= 0 or self.user_spend_ceiling_hqc > self.monthly_hqc_budget:
            raise ValueError("User spend ceiling must be positive and within the monthly budget")
        return self


def operational_max_cost(
    predicted_hqc: float,
    *,
    budget: float = 3000,
    reserve: float = 50,
    allowance: float = 100,
    user_ceiling: float | None = None,
) -> float:
    """Derive a cap with a fixed reserve and transparent prediction allowance."""
    if predicted_hqc <= 0 or budget <= reserve:
        raise ValueError("Invalid budget or provider estimate")
    effective_budget = min(budget, user_ceiling) if user_ceiling is not None else budget
    if effective_budget <= reserve:
        raise ValueError("Effective budget must exceed reserve")
    return round(min(effective_budget - reserve, predicted_hqc + allowance), 2)


class CampaignStore:
    def __init__(self, root: Path):
        self.root = root
        self.directory = root / "hardware_campaign"
        self.path = self.directory / "campaign_state.json"

    def load(self) -> CampaignState:
        if not self.path.is_file():
            raise FileNotFoundError(f"Campaign state does not exist: {self.path}")
        return CampaignState.model_validate_json(self.path.read_text())

    def save(self, state: CampaignState) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="campaign_state.", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(state.model_dump_json(indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def initialize(self, *, source: Path, qir: Path, bitcode: Path, protocol_version: str = "3.0", recommended_shots: int | None = 200, predicted_hqc: float | None = None, user_spend_ceiling_hqc: float = 1500) -> CampaignState:
        source_hash, qir_hash, bitcode_hash = sha256_file(source), sha256_file(qir), sha256_file(bitcode)
        if self.path.is_file():
            state = self.load()
            if (state.source_qasm_sha256, state.qir_sha256, state.qir_bitcode_sha256) != (source_hash, qir_hash, bitcode_hash):
                raise ValueError("Existing campaign state hashes do not match current frozen artifacts")
            return state
        state = CampaignState(
            source_qasm_sha256=source_hash,
            qir_sha256=qir_hash,
            qir_bitcode_sha256=bitcode_hash,
            protocol_version=protocol_version,
            recommended_shots_per_batch=recommended_shots,
            user_spend_ceiling_hqc=user_spend_ceiling_hqc,
            recommended_max_cost=operational_max_cost(predicted_hqc, user_ceiling=user_spend_ceiling_hqc) if predicted_hqc else None,
        )
        self.save(state)
        return state

    def create_batch(self, state: CampaignState, *, role: BatchRole, shots: int, max_cost: float | None = None) -> BatchRecord:
        batch_id = f"batch_{state.next_batch_number:03d}"
        if batch_id in state.batches:
            raise ValueError(f"Batch already exists: {batch_id}")
        if state.active_job is not None:
            raise ValueError("An active physical job already exists; use hardware-status or hardware-retrieve")
        if role == BatchRole.CONFIRMATION and state.candidate_freeze is None:
            raise ValueError("Batch 002 confirmation requires a frozen discovery candidate")
        batch = BatchRecord(batch_id=batch_id, role=role, source_qasm_sha256=state.source_qasm_sha256, qir_sha256=state.qir_sha256, qir_bitcode_sha256=state.qir_bitcode_sha256, protocol_hash=state.protocol_hash, requested_shots=shots, max_cost=max_cost)
        state.batches[batch_id] = batch
        state.next_batch_number += 1
        self.save(state)
        return batch

    def update_batch(self, state: CampaignState, batch_id: str, **updates: Any) -> BatchRecord:
        if batch_id not in state.batches:
            raise KeyError(batch_id)
        batch = state.batches[batch_id]
        for key, value in updates.items():
            if not hasattr(batch, key):
                raise ValueError(f"Unknown batch field: {key}")
            setattr(batch, key, value)
        batch.history.append({"timestamp": datetime.now(UTC).isoformat(), "updates": updates})
        if batch.status in {BatchStatus.SUBMITTED, BatchStatus.RUNNING}:
            state.active_job = {"batch_id": batch_id, "job_ref": batch.execution_job_ref}
            state.status = CampaignStatus.HARDWARE_BATCH_ACTIVE
        if batch.status in {BatchStatus.COMPLETED, BatchStatus.RETRIEVED, BatchStatus.NORMALIZED, BatchStatus.ANALYZED, BatchStatus.FAILED} and state.active_job and state.active_job.get("batch_id") == batch_id:
            state.active_job = None
        state.completed_batches = sorted(
            batch_id for batch_id, item in state.batches.items() if item.status in {BatchStatus.RETRIEVED, BatchStatus.NORMALIZED, BatchStatus.ANALYZED}
        )
        state.cumulative_valid_shots = sum(item.valid_shots for item in state.batches.values())
        if state.candidate_freeze is not None and state.status == CampaignStatus.PREPARED:
            state.status = CampaignStatus.DISCOVERY_CANDIDATE_FROZEN
        self.save(state)
        return batch
