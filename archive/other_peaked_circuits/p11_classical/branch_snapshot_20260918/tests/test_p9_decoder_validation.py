from pathlib import Path


def test_p9_decoder_validation_tool_exists() -> None:
    assert Path("scripts/validate_p9_decoder.py").is_file()
