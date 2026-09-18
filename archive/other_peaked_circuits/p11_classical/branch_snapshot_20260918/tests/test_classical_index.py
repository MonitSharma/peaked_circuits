from scripts.validate_classical_index import validate


def test_classical_index_is_valid() -> None:
    assert validate() == []
