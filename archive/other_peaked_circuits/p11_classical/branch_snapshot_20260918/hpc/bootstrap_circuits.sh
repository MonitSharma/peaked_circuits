#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE_ROOT="${P11_CIRCUIT_SOURCE_ROOT:-$ROOT/external/quantum-advantage-tracker}"
SOURCE_URL="${P11_CIRCUIT_SOURCE_URL:-https://github.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io.git}"
SOURCE_COMMIT="b60d2793558fcdfefeaadad78277e824dd4dfae4"
SOURCE_PATH="data/classically-verifiable-problems/circuit-models/peaked_circuit"
TARGET="$ROOT/data/canonical"

if [[ ! -d "$SOURCE_ROOT/.git" ]]; then
  mkdir -p "$(dirname "$SOURCE_ROOT")"
  git clone "$SOURCE_URL" "$SOURCE_ROOT"
fi
git -C "$SOURCE_ROOT" fetch --quiet origin "$SOURCE_COMMIT" || true
git -C "$SOURCE_ROOT" checkout --detach "$SOURCE_COMMIT"
mkdir -p "$TARGET"
for name in peaked_circuit_P9_Hqap_56x1917.qasm peaked_circuit_P11_Hqap_98x1999.qasm; do
  cp "$SOURCE_ROOT/$SOURCE_PATH/$name" "$TARGET/$name"
done
printf '%s\n' "source=$SOURCE_URL" "commit=$SOURCE_COMMIT" > "$TARGET/.hpc_circuit_provenance"
sha256sum "$TARGET"/*.qasm 2>/dev/null || shasum -a 256 "$TARGET"/*.qasm
