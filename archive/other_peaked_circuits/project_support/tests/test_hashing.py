from pathlib import Path

import pytest

from p12_recovery.hashing import sha256_file, verify_checksum


def test_stable_hash_and_changed_detection(tmp_path: Path) -> None:
    path = tmp_path / "value"
    path.write_bytes(b"abc")
    digest = sha256_file(path)
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert verify_checksum(path, digest)
    path.write_bytes(b"abcd")
    assert not verify_checksum(path, digest)


def test_missing_hash_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "missing")
