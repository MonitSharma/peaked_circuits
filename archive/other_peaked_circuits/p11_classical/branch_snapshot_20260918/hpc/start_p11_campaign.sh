#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BRANCH=$(git -C "$ROOT" branch --show-current)
if [[ "$BRANCH" != "p11_classical" && "${P11_ALLOW_OTHER_BRANCH:-0}" != "1" ]]; then
  echo "Refusing branch $BRANCH; checkout p11_classical or set P11_ALLOW_OTHER_BRANCH=1." >&2
  exit 2
fi
bash "$ROOT/hpc/bootstrap_env.sh"
bash "$ROOT/hpc/bootstrap_circuits.sh"
bash "$ROOT/hpc/preflight.sh"
if [[ -f "$ROOT/results/p11_hpc/ACTIVE_PID" ]]; then
  old=$(cat "$ROOT/results/p11_hpc/ACTIVE_PID")
  if kill -0 "$old" 2>/dev/null; then echo "Campaign already running with PID $old" >&2; exit 3; fi
fi
campaign_id=$(date -u +%Y%m%d_%H%M%S)
campaign="$ROOT/results/p11_hpc/$campaign_id"
mkdir -p "$campaign"
log="$campaign/campaign.log"
nohup setsid "$ROOT/.venv-hpc/bin/python" "$ROOT/scripts/run_p11_hpc_campaign.py" --campaign-dir "$campaign" >"$log" 2>&1 < /dev/null &
pid=$!
printf '%s\n' "$pid" > "$campaign/PID"
mkdir -p "$ROOT/results/p11_hpc"
printf '%s\n' "$pid" > "$ROOT/results/p11_hpc/ACTIVE_PID"
printf '%s\n' "$campaign" > "$ROOT/results/p11_hpc/ACTIVE_CAMPAIGN"
printf 'Campaign: %s\nPID: %s\nLog: %s\nResult directory: %s\nMonitor: bash %s/hpc/status.sh\nStop: bash %s/hpc/stop_campaign.sh\nResume: bash %s/hpc/resume_campaign.sh\n' "$campaign_id" "$pid" "$log" "$campaign" "$ROOT" "$ROOT" "$ROOT"
