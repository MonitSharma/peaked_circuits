import json
import subprocess
from pathlib import Path

from p12_recovery.models import AvailableDevicesReport
from p12_recovery.reporting import write_json


def test_generated_report_redacts_absolute_paths_and_records_commit(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    seed = tmp_path / "seed.txt"
    seed.write_text("seed")
    subprocess.run(["git", "add", "seed.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    output = tmp_path / "results/report.json"
    report = AvailableDevicesReport(
        status="failed",
        input_hashes={str(tmp_path / "private" / "input.dat"): "abc"},
    )
    write_json(output, report)
    text = output.read_text()
    payload = json.loads(text)
    assert ("/" + "Users/") not in text
    assert ("/" + "home/") not in text
    assert payload["git_commit"]
    assert payload["input_hashes"] == {"private/input.dat": "abc"}
