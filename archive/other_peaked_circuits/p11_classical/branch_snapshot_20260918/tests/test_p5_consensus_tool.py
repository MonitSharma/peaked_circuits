from pathlib import Path


def test_p5_consensus_tool_exists() -> None:
    assert Path("scripts/build_p5_consensus.py").is_file()
