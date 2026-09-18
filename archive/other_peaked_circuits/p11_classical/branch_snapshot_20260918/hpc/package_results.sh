#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
campaign="${1:-}"
if [[ -z "$campaign" && -f "$ROOT/results/p11_hpc/ACTIVE_CAMPAIGN" ]]; then campaign=$(cat "$ROOT/results/p11_hpc/ACTIVE_CAMPAIGN"); fi
[[ -d "$campaign" ]] || { echo "Provide a campaign directory." >&2; exit 2; }
out="${2:-$campaign.tar.gz}"
(cd "$campaign" && find . -type f ! -name '*.ckpt' ! -name '*.pkl' ! -name '*.pickle' -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
tar -czf "$out" -C "$(dirname "$campaign")" "$(basename "$campaign")" --exclude='*.ckpt' --exclude='*.pkl' --exclude='*.pickle'
echo "Packaged results: $out"
