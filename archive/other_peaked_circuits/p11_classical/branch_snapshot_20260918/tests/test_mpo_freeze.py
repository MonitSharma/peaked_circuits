from pathlib import Path


def test_mpo_freeze_tool_exists() -> None:
    assert Path("scripts/freeze_mpo_candidates.py").is_file()
