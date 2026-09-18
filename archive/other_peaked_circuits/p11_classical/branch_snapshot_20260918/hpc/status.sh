#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
base="$ROOT/results/p11_hpc"
campaign="${1:-}"
if [[ -z "$campaign" && -f "$base/ACTIVE_CAMPAIGN" ]]; then campaign=$(cat "$base/ACTIVE_CAMPAIGN"); fi
if [[ -z "$campaign" ]]; then echo "No active campaign."; exit 1; fi
echo "Campaign: $campaign"
if [[ -f "$campaign/PID" ]]; then
  pid=$(cat "$campaign/PID")
  if kill -0 "$pid" 2>/dev/null; then echo "Process: $pid (running)"; else echo "Process: $pid (not running)"; fi
fi
if [[ -f "$campaign/RUN_STATE.json" ]]; then
  "$ROOT/.venv-hpc/bin/python" - "$campaign/RUN_STATE.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
print("Status:", s.get("status", "RUNNING"))
print("Next stage:", s.get("next_stage"))
for name, rec in s.get("stages", {}).items(): print(f"{name}: {rec.get('status')}")
PY
fi
latest=$(find "$campaign" -name '*.log' -type f -print 2>/dev/null | sort | tail -1 || true)
if [[ -n "$latest" ]]; then echo "Latest log: $latest"; tail -n 20 "$latest"; fi
