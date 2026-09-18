#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
base="$ROOT/results/p11_hpc"
campaign="${1:-}"
if [[ -z "$campaign" && -f "$base/ACTIVE_CAMPAIGN" ]]; then campaign=$(cat "$base/ACTIVE_CAMPAIGN"); fi
[[ -n "$campaign" && -f "$campaign/RUN_STATE.json" ]] || { echo "Provide a campaign directory with RUN_STATE.json." >&2; exit 2; }
if [[ -f "$base/ACTIVE_PID" ]] && kill -0 "$(cat "$base/ACTIVE_PID")" 2>/dev/null; then echo "A campaign is already running." >&2; exit 3; fi
log="$campaign/resume_$(date -u +%Y%m%d_%H%M%S).log"
nohup setsid "$ROOT/.venv-hpc/bin/python" "$ROOT/scripts/run_p11_hpc_campaign.py" --campaign-dir "$campaign" --resume >"$log" 2>&1 < /dev/null &
pid=$!
printf '%s\n' "$pid" > "$campaign/PID"
printf '%s\n' "$pid" > "$base/ACTIVE_PID"
printf '%s\n' "$campaign" > "$base/ACTIVE_CAMPAIGN"
echo "Resumed $campaign (PID $pid); log $log"
