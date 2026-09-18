import json
from pathlib import Path


def test_hardware_index_matches_schema_and_saved_artifacts() -> None:
    root = Path(__file__).parents[1]
    index = json.loads((root / "results/quantinuum/hardware_index.json").read_text())
    schema = json.loads((root / "schemas/hardware_index.schema.json").read_text())
    assert schema["properties"]["branch"]["const"] == index["branch"]
    assert schema["properties"]["backend"]["const"] == index["backend"]
    required = set(schema["properties"]["problems"]["items"]["required"])
    assert {item["problem"] for item in index["problems"]} == {"P11", "P12"}
    for item in index["problems"]:
        assert required <= item.keys()
        assert len(item["source_sha256"]) == 64
        assert (root / item["source_qasm_path"]).is_file()
        assert (root / item["raw_artifact_path"]).is_file()
        assert (root / item["analysis_path"]).is_file()
