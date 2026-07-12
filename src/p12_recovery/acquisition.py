from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .constants import CIRCUIT_ID, REGISTRY_PATH, TRACKER_API, TRACKER_REPOSITORY
from .hashing import sha256_bytes, sha256_file
from .models import SourceArtifact
from .reporting import package_versions, write_json


def _get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "p12-helios-recovery/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _get_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "p12-helios-recovery/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return cast(bytes, response.read())


def resolve_registry_entry(
    registry: dict[str, Any], circuit_id: str = CIRCUIT_ID
) -> tuple[str, dict[str, Any]]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for model, descriptor in registry.items():
        for entry in descriptor.get("instances", []):
            if entry.get("id") == circuit_id:
                matches.append((model, entry))
    if len(matches) != 1:
        raise ValueError(
            f"Expected one exact registry entry for {circuit_id}, found {len(matches)}"
        )
    return matches[0]


def fetch_source(root: Path, *, replace_source: bool = False) -> SourceArtifact:
    destination = root / "circuits/original" / f"{CIRCUIT_ID}.qasm"
    metadata_path = root / "circuits/original/source_metadata.json"
    try:
        registry = _get_json(f"{TRACKER_API}/contents/{REGISTRY_PATH}?ref=main")
        registry_bytes = __import__("base64").b64decode(registry["content"])
        registry_data = json.loads(registry_bytes)
        model, entry = resolve_registry_entry(registry_data)
        source_path = f"data/classically-verifiable-problems/circuit-models/{model}/{entry['path']}"
        commit_data = _get_json(f"{TRACKER_API}/commits?path={source_path}&per_page=1")
        commit_sha = commit_data[0]["sha"] if commit_data else None
        raw_url = f"https://raw.githubusercontent.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io/{commit_sha or 'main'}/{source_path}"
        content = _get_bytes(raw_url)
    except (OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        if destination.is_file() and metadata_path.is_file():
            existing = SourceArtifact.model_validate_json(metadata_path.read_text())
            if sha256_file(destination) != existing.sha256:
                raise RuntimeError("Offline source differs from recorded metadata") from exc
            return existing
        raise RuntimeError(
            f"Unable to retrieve registry and no verified local source exists: {exc}"
        ) from exc
    digest = sha256_bytes(content)
    if destination.exists():
        existing_digest = sha256_file(destination)
        if existing_digest != digest and not replace_source:
            raise FileExistsError(
                f"Upstream source changed ({existing_digest} -> {digest}); pass --replace-source explicitly"
            )
        if existing_digest == digest:
            content = destination.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or replace_source:
        destination.write_bytes(content)
    sums = destination.parent / "SHA256SUMS"
    sums.write_text(f"{digest}  {destination.name}\n")
    artifact = SourceArtifact(
        circuit_id=CIRCUIT_ID,
        source_repository=TRACKER_REPOSITORY,
        source_path=source_path,
        retrieval_timestamp_utc=datetime.now(UTC),
        source_commit_sha=commit_sha,
        local_path=str(destination),
        file_size_bytes=len(content),
        sha256=digest,
        package_versions=package_versions(),
        input_hashes={REGISTRY_PATH: sha256_bytes(registry_bytes)},
    )
    write_json(metadata_path, artifact)
    return artifact
