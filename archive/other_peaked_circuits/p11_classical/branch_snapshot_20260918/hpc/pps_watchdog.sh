#!/usr/bin/env bash
set -euo pipefail
PID="${1:?pid required}"
OUT="${2:?telemetry path required}"
RSS_LIMIT_KB="${PPS_RSS_LIMIT_KB:-83886080}"
SWAP_LIMIT_KB="${PPS_SWAP_LIMIT_KB:-262144}"
mkdir -p "$(dirname "$OUT")"
echo 'timestamp,vmrss_kb,vmpeak_kb,vmswap_kb,action' > "$OUT"
while kill -0 "$PID" 2>/dev/null; do
  status="/proc/$PID/status"
  [[ -r "$status" ]] || break
  rss=$(awk '$1=="VmRSS:"{print $2}' "$status")
  peak=$(awk '$1=="VmPeak:"{print $2}' "$status")
  swap=$(awk '$1=="VmSwap:"{print $2}' "$status")
  action="observe"
  if (( swap > SWAP_LIMIT_KB || rss > RSS_LIMIT_KB )); then
    action="terminate_resource_limit"
    echo "$(date -Is),$rss,$peak,$swap,$action" >> "$OUT"
    kill -TERM "$PID" 2>/dev/null || true
    break
  fi
  echo "$(date -Is),$rss,$peak,$swap,$action" >> "$OUT"
  sleep "${PPS_WATCHDOG_INTERVAL:-10}"
done
