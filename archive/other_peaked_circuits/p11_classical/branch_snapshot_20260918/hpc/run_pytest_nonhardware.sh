#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec "$ROOT/.venv-hpc/bin/python" -m pytest -q -m 'not hardware'
