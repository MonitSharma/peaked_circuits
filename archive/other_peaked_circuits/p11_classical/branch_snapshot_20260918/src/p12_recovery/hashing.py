import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Cannot hash missing file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_config(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_bytes(payload.encode())


def verify_checksum(path: Path, expected: str) -> bool:
    return sha256_file(path) == expected.lower()


def read_sha256sums(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing checksum file: {path}")
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        digest, filename = line.split(maxsplit=1)
        result[filename.lstrip(" *")] = digest
    return result
