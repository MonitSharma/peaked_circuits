#!/usr/bin/env python3
"""Verify the self-contained P11/P12 tracker evidence packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "results" / "tracker_submissions"
PACKAGES = ("p11", "p12")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def verify_package(name: str) -> None:
    package = ROOT / name
    record_path = package / "tracker_submission.json"
    if not package.is_dir() or not record_path.is_file():
        fail(f"missing package or tracker record: {name}")

    record = json.loads(record_path.read_text())
    answer = record["answer"]
    if len(answer) != 98 or set(answer) - {"0", "1"}:
        fail(f"{name}: answer is not a 98-bit binary string")
    if record["value"] != "100%" or record["quantumAdvantageClaim"] is not False:
        fail(f"{name}: tracker claim fields are inconsistent")

    # The exact source and canonical shot files are the minimum evidence that
    # must survive packaging. The full provider artifacts are also hashed.
    required = [
        package / "TRACKER_SUBMISSION.md",
        package / "quantum" / "source",
        package / "quantum" / "job.json",
        package / "quantum" / "provider_manifest.json",
        package / "timing.md",
        package / "classical",
    ]
    for path in required:
        if not path.exists():
            fail(f"{name}: missing required evidence {path.relative_to(package)}")

    hashes = package / "SHA256SUMS"
    if not hashes.is_file():
        fail(f"{name}: missing SHA256SUMS")
    checked = 0
    for line in hashes.read_text().splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        target = package / relative
        if not target.is_file():
            fail(f"{name}: hash target missing: {relative}")
        actual = sha256(target)
        if actual != digest:
            fail(f"{name}: SHA256 mismatch: {relative}")
        checked += 1
    if checked == 0:
        fail(f"{name}: empty SHA256SUMS")

    print(f"PASS {name}: 98-bit answer, required artifacts, {checked} hashes")


def main() -> None:
    for name in PACKAGES:
        verify_package(name)


if __name__ == "__main__":
    main()

