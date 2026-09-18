#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
base="$ROOT/results/p11_hpc"
[[ -f "$base/ACTIVE_PID" ]] || { echo "No active campaign."; exit 1; }
pid=$(cat "$base/ACTIVE_PID")
if ! kill -0 "$pid" 2>/dev/null; then echo "PID $pid is not running."; exit 0; fi
echo "Sending TERM to campaign process group $pid"
kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid"
for _ in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || { echo "Campaign stopped."; exit 0; }; sleep 1; done
echo "Campaign did not exit after 30s; sending KILL." >&2
kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid"
