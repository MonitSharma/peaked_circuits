#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# P11 overnight bond/cutoff ladder — Apple M3 Pro (12 core, 36 GiB), safe mode.
#
# Tests the hypothesis in docs/P11_REASSESSMENT.md: the P11 stall is caused by
# running the reference MPO+unswapping algorithm at 1/16 the reference bond
# ceiling with a 3x tighter cutoff, not by an entanglement barrier.
#
# SAFETY: per-run RSS watchdog, per-run wall clock cap, capped thread budget,
# strictly sequential runs, no sudo, no swap tuning. Observed peak RSS across
# the 162 historical P11 runs was 5.42 GB; the watchdog here trips at 18 GB.
#
# BLINDNESS: every P11 invocation passes --expected-bitstring "" . No tracker
# answer, emulator output, or hardware result is read.
#
# Usage:   bash scripts/p11_overnight_ladder.sh            # full ladder
#          STAGE0_ONLY=1 bash scripts/p11_overnight_ladder.sh   # P9 check only
# ---------------------------------------------------------------------------
set -uo pipefail

SOLVER="${SOLVER:-$HOME/code_projects/qat/peaked-mpo-solver}"
SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_PY="$SCRIPT_ROOT/.venv-p9-isolated/bin/python"
[ -x "$HOME/.conda/envs/p9-openblas/bin/python" ] && DEFAULT_PY="$HOME/.conda/envs/p9-openblas/bin/python"
[ -x "$DEFAULT_PY" ] || DEFAULT_PY="$SOLVER/.venv/bin/python"
PY="${SOLVER_PYTHON:-$DEFAULT_PY}"
CIRCUITS="${CIRCUITS:-$HOME/code_projects/qat/tracker/data/classically-verifiable-problems/circuit-models/peaked_circuit}"
P9="$CIRCUITS/peaked_circuit_P9_Hqap_56x1917.qasm"
P11="$CIRCUITS/peaked_circuit_P11_Hqap_98x1999.qasm"
OUT="${OUT:-$HOME/Code/p12-helios-recovery/results/p11_bond_ladder/$(date -u +%Y%m%d_%H%M%S)}"

RSS_LIMIT_GB="${RSS_LIMIT_GB:-18}"      # hard kill; machine has 36 GiB
THREADS="${THREADS:-1}"                  # validated low-memory BLAS configuration
P9_CONTROL_WALL_S="${P9_CONTROL_WALL_S:-14400}" # isolated full-P9 gate
POLL_S=10

mkdir -p "$OUT"
MASTER="$OUT/ladder.log"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$MASTER"; }

# ---------------------------------------------------------------- preflight --
log "=== preflight ==="
for f in "$SOLVER/src/p9solver/cli.py" "$P9" "$P11" "$PY"; do
  [ -e "$f" ] || { log "MISSING: $f"; exit 2; }
done
# The in-place MPO normalization was removed after reproducing a macOS
# Accelerate/BLAS SIGSEGV around P9 gate 106. The QR guard remains required.
if grep -q "equalize_norms_(1.0)" "$SOLVER/src/p9solver/mpo.py"; then
  log "FATAL: unsafe in-place MPO normalization is present in mpo.py"; exit 3
fi
[ -f "$SOLVER/src/p9solver/_quimb_compat.py" ] \
  || { log "FATAL: quimb QR guard missing — apply solver_maxswap_patch.diff"; exit 3; }
log "solver hardening present (QR guard; unsafe norm mutation absent)"

FREE_GB=$(df -g "$HOME" | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 20 ] || { log "FATAL: only ${FREE_GB} GiB free disk; need 20+"; exit 4; }
log "disk free: ${FREE_GB} GiB | threads: $THREADS | RSS watchdog: ${RSS_LIMIT_GB} GB"
log "python: $PY"
log "output: $OUT"

export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS OPENBLAS_NUM_THREADS=$THREADS
export NUMBA_NUM_THREADS=$THREADS VECLIB_MAXIMUM_THREADS=$THREADS BLIS_NUM_THREADS=$THREADS
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-$OUT/numba_cache}"
export PYTHONPATH="$SOLVER/src${PYTHONPATH:+:$PYTHONPATH}"

# ------------------------------------------------------- guarded run driver --
# run_guarded <name> <wall_limit_s> <solver args...>
run_guarded() {
  local name="$1"; shift
  local wall="$1"; shift
  local dir="$OUT/$name"
  mkdir -p "$dir"
  log "--- START $name (wall cap $((wall/60)) min) ---"
  printf '%s\n' "$*" > "$dir/command.txt"

  ( cd "$SOLVER" && "$PY" -m p9solver.cli "$@" --outdir "$dir" --tag r ) \
      > "$dir/run.log" 2>&1 &
  local pid=$!
  local start peak_kb=0
  start=$(date +%s)

  # Normally the solver is one process, but BLAS/Numba or a future launcher
  # can leave descendants behind. Kill the complete descendant tree when a
  # watchdog or wall limit fires.
  kill_tree() {
    local root_pid="$1" signal_name="$2" child_pid
    [ -n "$root_pid" ] || return 0
    while read -r child_pid; do
      [ -n "$child_pid" ] || continue
      kill_tree "$child_pid" "$signal_name"
    done < <(ps -Ao pid=,ppid= | awk -v root="$root_pid" '$2 == root {print $1}')
    kill -"$signal_name" "$root_pid" 2>/dev/null || true
  }

  while kill -0 "$pid" 2>/dev/null; do
    # sum RSS over the whole process subtree
    local kb
    kb=$(ps -Ao pid=,ppid=,rss= | awk -v root="$pid" '
      { rss[$1]=$3; par[$1]=$2 }
      END { for (p in rss) { q=p; d=0
              while (q!="" && q!=1 && d<64) { if (q==root) { t+=rss[p]; break } q=par[q]; d++ } }
            print t+0 }')
    [ "$kb" -gt "$peak_kb" ] && peak_kb=$kb
    if [ "$kb" -gt $((RSS_LIMIT_GB * 1024 * 1024)) ]; then
      log "!! WATCHDOG: RSS $((kb/1024/1024)) GB > ${RSS_LIMIT_GB} GB — terminating $name"
      kill_tree "$pid" TERM; sleep 10; kill_tree "$pid" KILL
      echo "rss_watchdog" > "$dir/termination.txt"; break
    fi
    if [ $(( $(date +%s) - start )) -gt "$wall" ]; then
      log "!! wall cap reached — terminating $name"
      kill_tree "$pid" TERM; sleep 10; kill_tree "$pid" KILL
      echo "wall_limit" > "$dir/termination.txt"; break
    fi
    sleep "$POLL_S"
  done
  wait "$pid" 2>/dev/null; local rc=$?
  [ -f "$dir/termination.txt" ] || echo "exit_$rc" > "$dir/termination.txt"

  local elapsed=$(( $(date +%s) - start ))
  printf '{"name":"%s","termination":"%s","wall_s":%d,"peak_rss_gb":%.2f}\n' \
    "$name" "$(cat "$dir/termination.txt")" "$elapsed" \
    "$(echo "$peak_kb" | awk '{print $1/1048576}')" > "$dir/guard_record.json"
  log "--- END $name: $(cat "$dir/termination.txt") | $((elapsed/60)) min | peak RSS $(echo "$peak_kb" | awk '{printf "%.1f", $1/1048576}') GB"
  "$PY" - "$dir" <<'PYEOF' 2>/dev/null | tee -a "$MASTER"
import json,sys,glob
for p in glob.glob(sys.argv[1]+"/**/summary.json",recursive=True):
    d=json.load(open(p))
    t=d.get("truncation_diagnostics") or {}
    print("    work_consumed=%s  reason=%s  peak_bond=%s  peak_elems=%s"%(
        d.get("last_work_consumed"), d.get("termination_reason"),
        d.get("peak_max_bond"), d.get("peak_total_elems")))
    print("    bond_cap=%s  rows_at_cap=%s  first_stage_at_cap=%s   <-- cap binding?"%(
        t.get("max_bond_limit"), t.get("rows_at_max_bond"), t.get("first_stage_at_max_bond")))
PYEOF
}

COMMON=( --unswap-threshold 1000000 --max-its 20 --seed 123 --center-ratio 0.5
         --sabre-trials 90 --post-sabre-trials 20
         --route-candidates 2 --route-score lookahead_total --route-score-lookahead 8
         --route-seed-stride 1009
         --abort-after-no-progress-unswap-cycles 40
         --console-log-level INFO )
# NOTE: deliberately NOT passing --unswap-trigger-max-bond (historical runs
# clamped it to 128) and NOT passing --max-work-gates (historical runs capped
# at 250). Both clamps are part of what this ladder is testing.

# ------------------------------------------------ stage 0: P9 sanity + RSS ---
# A full P9 run at D4096 is not a useful gate: the high-bond unswap probes can
# be much slower than the historical D512 control. First validate the new
# high-bond path with a bounded probe, then run the known-good full P9 control.
# This is the ONLY stage that checks an expected bitstring.
log "=== stage 0: bounded D4096 probe + full P9 control ==="
run_guarded "stage0_p9_probe_cut2e3_D4096" 900 \
  --qasm "$P9" --cutoff 0.002 --max-bond 4096 --max-work-gates 8 --skip-sampling "${COMMON[@]}"

run_guarded "stage0_p9_control_cut6e4_D512" "$P9_CONTROL_WALL_S" \
  --qasm "$P9" --cutoff 0.0006 --max-bond 512 --samples 1000 \
  --unswap-trigger-max-bond 128 "${COMMON[@]}"

if grep -q '"matches_expected_bitstring": true' "$OUT/stage0_p9_control_cut6e4_D512"/*/summary.json 2>/dev/null \
   || grep -q '"matches_expected_bitstring": true' "$OUT/stage0_p9_control_cut6e4_D512"/summary.json 2>/dev/null; then
  log "stage 0 PASS: full P9 control reproduced at cutoff 6e-4 / bond 512"
else
  log "stage 0 FAIL: P9 control did not reproduce. Do NOT trust the ladder."
  exit 5
fi

[ "${STAGE0_ONLY:-0}" = "1" ] && { log "STAGE0_ONLY set — stopping."; exit 0; }

# ------------------------------------------------------ stage 1: P11 ladder --
# Four runs, ~2h each. R1/R2 isolate the two variables; R3 is the reference-like
# config; R4 exploits the fact that only argmax is needed, not fidelity.
log "=== stage 1: P11 ladder (4 x 2h, P11 stays blind) ==="

run_guarded "R1_cut2e3_D512"  7200 --qasm "$P11" --expected-bitstring "" --cutoff 0.002  --max-bond 512  --skip-sampling "${COMMON[@]}"
run_guarded "R2_cut6e4_D4096" 7200 --qasm "$P11" --expected-bitstring "" --cutoff 0.0006 --max-bond 4096 --skip-sampling "${COMMON[@]}"
run_guarded "R3_cut2e3_D4096" 7200 --qasm "$P11" --expected-bitstring "" --cutoff 0.002  --max-bond 4096 --skip-sampling "${COMMON[@]}"
run_guarded "R4_cut5e3_D4096" 7200 --qasm "$P11" --expected-bitstring "" --cutoff 0.005  --max-bond 4096 --skip-sampling "${COMMON[@]}"

log "=== ladder complete ==="
log "Baseline to beat: 142 / 1984 work gates (best historical faithful P11 run)."
log "Summary:"
for d in "$OUT"/R*/; do
  printf '  %-22s %s\n' "$(basename "$d")" "$(cat "$d/termination.txt" 2>/dev/null)" | tee -a "$MASTER"
done
