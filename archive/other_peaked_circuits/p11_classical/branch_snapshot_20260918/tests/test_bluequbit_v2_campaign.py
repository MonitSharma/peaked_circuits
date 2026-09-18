from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_campaign_dry_run_reuses_existing_artifacts(tmp_path):
    state = tmp_path / "state.json"
    result = subprocess.run([sys.executable, "scripts/run_bluequbit_p1_v2.py", "--state", str(state), "--stage", "PROFILE"], capture_output=True, text=True, check=True)
    assert "skip (valid artifacts)" in result.stdout
    assert json.loads(state.read_text())["stages"]["PROFILE"]["status"] == "COMPLETE_ARTIFACT_REUSED"
