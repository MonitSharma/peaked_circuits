#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SOLVER_ROOT="${P11_SOLVER_ROOT:-$ROOT/external/peaked-mpo-solver}"
SOLVER_URL="${P11_SOLVER_URL:-https://github.com/alexgalda-m/peaked-mpo-solver.git}"
SOLVER_COMMIT="3bcdc1e5bfd6abb9425f71bd43e560d2b27f45c1"
PATCH_DIR="$ROOT/hpc/solver_patches"

if [[ ! -d "$SOLVER_ROOT/.git" ]]; then
  mkdir -p "$(dirname "$SOLVER_ROOT")"
  git clone "$SOLVER_URL" "$SOLVER_ROOT"
fi
git -C "$SOLVER_ROOT" fetch --quiet --tags origin "$SOLVER_COMMIT" || true
git -C "$SOLVER_ROOT" checkout --detach "$SOLVER_COMMIT"

if [[ ! -f "$SOLVER_ROOT/.p11_hpc_patch_applied" ]]; then
  git -C "$SOLVER_ROOT" apply --check "$PATCH_DIR/0001-research-hardening.patch"
  git -C "$SOLVER_ROOT" apply "$PATCH_DIR/0001-research-hardening.patch"
  cp "$PATCH_DIR/src_p9solver__quimb_compat.py" "$SOLVER_ROOT/src/p9solver/_quimb_compat.py"
  printf '%s\n' "solver=$SOLVER_URL" "base_commit=$SOLVER_COMMIT" "patch=0001-research-hardening.patch" > "$SOLVER_ROOT/.p11_hpc_patch_applied"
fi

printf 'solver_root=%s\nsolver_url=%s\nbase_commit=%s\n' "$SOLVER_ROOT" "$SOLVER_URL" "$SOLVER_COMMIT"
