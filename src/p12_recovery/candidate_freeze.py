"""Candidate freezing is deliberately target-blind and hash-addressed."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .hashing import hash_config, sha256_bytes, sha256_file


def validate_candidate(candidate: str) -> str:
    if len(candidate) != 98 or set(candidate) - {"0", "1"}:
        raise ValueError("P12 candidate must be exactly 98 canonical binary bits")
    return candidate


def freeze_candidate(candidate: str, *, counts: dict[str, int], source_paths: list[Path], protocol_hash: str) -> dict[str, Any]:
    validate_candidate(candidate)
    canonical = json.dumps({"candidate": candidate, "counts": dict(sorted(counts.items()))}, sort_keys=True, separators=(",", ":"))
    return {"status": "frozen", "candidate": candidate, "candidate_sha256": sha256_bytes(candidate.encode()), "canonical_input_sha256": sha256_bytes(canonical.encode()), "source_hashes": {str(path): sha256_file(path) for path in source_paths}, "protocol_hash": protocol_hash, "external_target_scored": False, "target_accessed": False, "freeze_hash": hash_config({"candidate": candidate, "canonical_input_sha256": sha256_bytes(canonical.encode()), "protocol_hash": protocol_hash})}
