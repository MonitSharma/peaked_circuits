"""Parse and rescore all usable P9/P11/P12 solver trajectories.

Two solver families write different artefacts under the project working tree:

* p9solver (MPO + greedy unswapping): writes ``live_stats.jsonl`` with per-stage
  records and a ``progress_checkpoint.json`` holding the full option set.  The
  routing trajectory lives in ``unswap_cycle_summary`` / ``cycle_progress``
  records (one per unswap cycle) and in ``rewiring`` records.
* MettleQ MPS prefix engine: writes ``manifest.json`` (kind
  ``blind-p11-mps-prefix``), ``summary.json`` and ``progress.jsonl``.

This script walks a set of roots, classifies each run, extracts primitive
metrics after each rewire/cycle, and emits one master CSV plus a per-run
trajectory CSV.  It never reads any expected bitstring; it only consumes
solver telemetry.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

# Known circuit hashes -> label, so runs are classified without trusting the
# free-text path (paths differ across machines/worktrees).
CIRCUIT_BY_SHA = {
    "1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372": "P11",
}


def _sha_label(sha: Optional[str], qasm: Optional[str]) -> str:
    if sha and sha in CIRCUIT_BY_SHA:
        return CIRCUIT_BY_SHA[sha]
    if qasm:
        low = qasm.lower()
        for tag in ("p9", "p11", "p12", "heavy_hex"):
            if tag in low:
                return tag.upper()
    return "unknown"


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _iter_jsonl(path: Path) -> Iterable[dict]:
    try:
        with path.open() as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except OSError:
        return


@dataclass
class RunSummary:
    name: str
    path: str
    family: str  # 'mpo' or 'mps'
    circuit: str
    # config knobs (mpo)
    cutoff: Optional[float] = None
    max_bond: Optional[int] = None
    center_ratio: Optional[float] = None
    unswap_threshold: Optional[float] = None
    unswap_select_mode: Optional[str] = None
    route_proxy_weight: Optional[float] = None
    route_proxy_lookahead: Optional[int] = None
    route_proxy_policy: Optional[str] = None
    alignment_weight: Optional[float] = None
    max_swaps_per_step: Optional[int] = None
    trigger_max_bond: Optional[int] = None
    dtype: Optional[str] = None
    max_work_gates: Optional[int] = None
    seed: Optional[int] = None
    # config knobs (mps)
    dmax: Optional[int] = None
    eps: Optional[float] = None
    routing_strategy: Optional[str] = None
    routing_lookahead: Optional[int] = None
    # outcome / trajectory
    total_work_gates: Optional[int] = None
    gates_completed: Optional[int] = None
    wall_time_s: Optional[float] = None
    cycles: Optional[int] = None
    peak_max_bond: Optional[int] = None
    peak_total_elems: Optional[int] = None
    peak_rss_bytes: Optional[int] = None
    no_progress_cycles_final: Optional[int] = None
    status: Optional[str] = None
    # rescored progress metrics
    gates_per_hour: Optional[float] = None
    gates_last_third: Optional[int] = None
    time_last_third_s: Optional[float] = None
    rate_last_third_gph: Optional[float] = None
    stalled: Optional[bool] = None
    # stage time breakdown (fraction of wall)
    frac_unswap: Optional[float] = None
    frac_rewire: Optional[float] = None
    frac_absorb: Optional[float] = None
    # mps specifics
    discarded_weight_sum: Optional[float] = None
    mps_bond_mean_final: Optional[float] = None
    planned_lookahead_swaps: Optional[int] = None
    planned_restore_swaps: Optional[int] = None
    trajectory: list[dict] = field(default_factory=list)


def parse_mpo_run(name: str, run_dir: Path) -> Optional[RunSummary]:
    live = run_dir / "live_stats.jsonl"
    if not live.is_file():
        return None
    cfg = _read_json(run_dir / "progress_checkpoint.json") or {}
    if not cfg.get("options"):
        # p11_research runs store config in manifest.json instead.
        man = _read_json(run_dir / "manifest.json") or {}
        if man.get("options"):
            cfg = man
    opts = cfg.get("options", {}) if isinstance(cfg, dict) else {}
    circuit = _sha_label(cfg.get("qasm_sha256"), cfg.get("qasm") or opts.get("qasm"))

    s = RunSummary(
        name=name, path=str(run_dir), family="mpo", circuit=circuit,
        cutoff=opts.get("cutoff"), max_bond=opts.get("max_bond"),
        center_ratio=opts.get("center_ratio"),
        unswap_threshold=opts.get("unswap_threshold"),
        unswap_select_mode=opts.get("unswap_select_mode"),
        route_proxy_weight=opts.get("unswap_route_proxy_weight"),
        route_proxy_lookahead=opts.get("unswap_route_proxy_lookahead"),
        route_proxy_policy=opts.get("unswap_route_proxy_policy"),
        alignment_weight=opts.get("unswap_alignment_weight"),
        max_swaps_per_step=opts.get("unswap_max_swaps_per_step"),
        trigger_max_bond=opts.get("unswap_trigger_max_bond"),
        dtype=opts.get("dtype"),
        max_work_gates=opts.get("max_work_gates"),
        seed=opts.get("seed"),
    )

    # Walk records: build trajectory from cycle summaries, track peaks and
    # cumulative time-in-stage via consecutive-timestamp deltas.
    prev_t: Optional[float] = None
    prev_stage: Optional[str] = None
    stage_time: dict[str, float] = {}
    last_t = 0.0
    peak_bond = 0
    peak_elems = 0
    peak_rss = 0
    for rec in _iter_jsonl(live):
        t = rec.get("time")
        stage = rec.get("stage")
        if isinstance(t, (int, float)):
            if prev_t is not None and prev_stage is not None and t >= prev_t:
                stage_time[prev_stage] = stage_time.get(prev_stage, 0.0) + (t - prev_t)
            prev_t, prev_stage = t, stage
            last_t = max(last_t, t)
        mb = rec.get("max_bond")
        if isinstance(mb, int):
            peak_bond = max(peak_bond, mb)
        te = rec.get("total_elems")
        if isinstance(te, int):
            peak_elems = max(peak_elems, te)
        rss = rec.get("process_tree_rss_bytes") or rec.get("process_rss_bytes")
        if isinstance(rss, int):
            peak_rss = max(peak_rss, rss)
        if stage in ("unswap_cycle_summary", "cycle_progress"):
            if s.total_work_gates is None:
                s.total_work_gates = rec.get("total_work_gates")
            point = {
                "cycle": rec.get("unswap_cycle"),
                "time_s": t,
                "gates_consumed": rec.get("gates_consumed"),
                "remaining_work_gates": rec.get("remaining_work_gates"),
                "cycle_gates_consumed": rec.get("cycle_gates_consumed"),
                "max_bond": mb,
                "total_elems": te,
                "no_progress_cycles": rec.get("no_progress_unswap_cycles"),
                "unswap_applied_swaps": rec.get("unswap_applied_swaps"),
                "rewire_wall_time_s": rec.get("rewire_wall_time_s"),
                "stage": stage,
            }
            # Prefer cycle_summary rows (one per cycle); keep last per cycle.
            s.trajectory.append(point)

    s.wall_time_s = last_t
    s.peak_max_bond = peak_bond or None
    s.peak_total_elems = peak_elems or None
    s.peak_rss_bytes = peak_rss or None

    # Deduplicate trajectory by cycle, keeping the summary row when present.
    by_cycle: dict[Any, dict] = {}
    for p in s.trajectory:
        c = p["cycle"]
        if c not in by_cycle or p["stage"] == "unswap_cycle_summary":
            by_cycle[c] = p
    traj = [by_cycle[c] for c in sorted(by_cycle, key=lambda x: (x is None, x))]
    s.trajectory = traj

    completed_vals = [p["gates_consumed"] for p in traj if isinstance(p.get("gates_consumed"), int)]
    if completed_vals:
        s.gates_completed = max(completed_vals)
    s.cycles = len(traj) or None
    npc = [p["no_progress_cycles"] for p in traj if isinstance(p.get("no_progress_cycles"), int)]
    if npc:
        s.no_progress_cycles_final = npc[-1]

    # Stage time fractions.
    total_stage = sum(stage_time.values()) or 1.0
    s.frac_unswap = round(stage_time.get("unswapping", 0.0) / total_stage, 4)
    s.frac_rewire = round(stage_time.get("rewiring", 0.0) / total_stage, 4)
    s.frac_absorb = round(stage_time.get("absorbing", 0.0) / total_stage, 4)

    # Rescored progress: overall and last-third rates.
    if s.gates_completed and s.wall_time_s:
        s.gates_per_hour = round(s.gates_completed / s.wall_time_s * 3600.0, 2)
    _rescored_last_third(s, traj)
    return s


def _rescored_last_third(s: RunSummary, traj: list[dict]) -> None:
    pts = [p for p in traj if isinstance(p.get("gates_consumed"), int)
           and isinstance(p.get("time_s"), (int, float))]
    if len(pts) < 3:
        return
    n = len(pts)
    cut = pts[max(0, n - max(2, n // 3)) - 1] if n >= 3 else pts[0]
    start = pts[max(0, n - max(2, n // 3)) - 1]
    end = pts[-1]
    dg = end["gates_consumed"] - start["gates_consumed"]
    dt = end["time_s"] - start["time_s"]
    s.gates_last_third = dg
    s.time_last_third_s = round(dt, 2)
    if dt > 0:
        s.rate_last_third_gph = round(dg / dt * 3600.0, 2)
    # Stall: last-third made <2 gates of progress despite spending >20% of wall.
    if dt > 0 and s.wall_time_s and dt / s.wall_time_s > 0.2:
        s.stalled = dg < 2


def parse_mps_run(name: str, run_dir: Path) -> Optional[RunSummary]:
    manifest = _read_json(run_dir / "manifest.json")
    summary = _read_json(run_dir / "summary.json")
    if not manifest and not summary:
        return None
    src = summary or manifest or {}
    cfg = (manifest or {}).get("configuration", {}) or (summary or {}).get("configuration", {})
    routing = (summary or manifest or {}).get("routing", {})
    circuit = _sha_label((manifest or summary or {}).get("qasm_sha256"), cfg.get("qasm"))

    s = RunSummary(
        name=name, path=str(run_dir), family="mps", circuit=circuit,
        dmax=cfg.get("dmax"), eps=cfg.get("eps"),
        routing_strategy=cfg.get("routing_strategy"),
        routing_lookahead=cfg.get("lookahead"),
        max_work_gates=cfg.get("max_ops"),
        planned_lookahead_swaps=routing.get("planned_lookahead_swaps"),
        planned_restore_swaps=routing.get("planned_restore_swaps"),
    )
    s.status = (summary or {}).get("status")
    s.gates_completed = (summary or {}).get("operations_completed")
    s.wall_time_s = (summary or {}).get("elapsed_wall_time_s")
    diag = (summary or {}).get("diagnostics", {})
    s.discarded_weight_sum = diag.get("relative_discarded_weight_sum")
    last = diag.get("last_event", {})
    s.peak_max_bond = diag.get("maximum_bond_dimension_reached") or last.get("bond")
    # Trajectory from progress.jsonl
    for rec in _iter_jsonl(run_dir / "progress.jsonl"):
        s.trajectory.append({
            "operations": rec.get("operations"),
            "time_s": rec.get("elapsed_wall_time_s"),
            "bond_max": rec.get("current_bond_dimension_max") or rec.get("maximum_bond_dimension_reached"),
            "bond_mean": rec.get("current_bond_dimension_mean"),
            "discarded_weight_sum": rec.get("relative_discarded_weight_sum"),
            "rss_bytes": rec.get("process_rss_bytes"),
            "stage": rec.get("stage"),
        })
    if s.trajectory:
        s.mps_bond_mean_final = s.trajectory[-1].get("bond_mean")
        rss = [p["rss_bytes"] for p in s.trajectory if isinstance(p.get("rss_bytes"), int)]
        if rss:
            s.peak_rss_bytes = max(rss)
    if s.gates_completed and s.wall_time_s:
        s.gates_per_hour = round(s.gates_completed / s.wall_time_s * 3600.0, 2)
    return s


def classify_and_parse(run_dir: Path) -> Optional[RunSummary]:
    name = run_dir.name
    if (run_dir / "live_stats.jsonl").is_file():
        return parse_mpo_run(name, run_dir)
    if (run_dir / "manifest.json").is_file() and (run_dir / "summary.json").is_file():
        man = _read_json(run_dir / "manifest.json") or {}
        if "mps" in str(man.get("kind", "")) or (run_dir / "progress.jsonl").is_file():
            return parse_mps_run(name, run_dir)
    return None


def discover(roots: list[Path]) -> list[RunSummary]:
    runs: list[RunSummary] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] + [p for p in root.rglob("*") if p.is_dir()]
        for d in candidates:
            key = str(d.resolve())
            if key in seen:
                continue
            r = classify_and_parse(d)
            if r is not None:
                seen.add(key)
                runs.append(r)
    return runs


SUMMARY_FIELDS = [
    "name", "family", "circuit", "status",
    "cutoff", "max_bond", "center_ratio", "unswap_threshold",
    "unswap_select_mode", "route_proxy_weight", "route_proxy_lookahead",
    "route_proxy_policy", "alignment_weight", "max_swaps_per_step",
    "trigger_max_bond", "dtype", "max_work_gates", "seed",
    "dmax", "eps", "routing_strategy", "routing_lookahead",
    "total_work_gates", "gates_completed", "wall_time_s", "cycles",
    "peak_max_bond", "peak_total_elems", "peak_rss_bytes",
    "no_progress_cycles_final", "gates_per_hour",
    "gates_last_third", "time_last_third_s", "rate_last_third_gph", "stalled",
    "frac_unswap", "frac_rewire", "frac_absorb",
    "discarded_weight_sum", "mps_bond_mean_final",
    "planned_lookahead_swaps", "planned_restore_swaps", "path",
]


def write_summary_csv(runs: list[RunSummary], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        for r in runs:
            row = {k: getattr(r, k, None) for k in SUMMARY_FIELDS}
            w.writerow(row)


def write_trajectory_csv(runs: list[RunSummary], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["run", "family", "circuit", "cycle_or_ops", "time_s",
              "gates_or_ops_consumed", "remaining_work_gates", "max_bond",
              "total_elems", "bond_mean", "discarded_weight_sum",
              "no_progress_cycles", "unswap_applied_swaps", "rewire_wall_time_s"]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in runs:
            for p in r.trajectory:
                w.writerow({
                    "run": r.name, "family": r.family, "circuit": r.circuit,
                    "cycle_or_ops": p.get("cycle", p.get("operations")),
                    "time_s": p.get("time_s"),
                    "gates_or_ops_consumed": p.get("gates_consumed", p.get("operations")),
                    "remaining_work_gates": p.get("remaining_work_gates"),
                    "max_bond": p.get("max_bond", p.get("bond_max")),
                    "total_elems": p.get("total_elems"),
                    "bond_mean": p.get("bond_mean"),
                    "discarded_weight_sum": p.get("discarded_weight_sum"),
                    "no_progress_cycles": p.get("no_progress_cycles"),
                    "unswap_applied_swaps": p.get("unswap_applied_swaps"),
                    "rewire_wall_time_s": p.get("rewire_wall_time_s"),
                })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", required=True,
                    help="Directories to scan for run subdirectories.")
    ap.add_argument("--summary-csv", type=Path, required=True)
    ap.add_argument("--trajectory-csv", type=Path, required=True)
    args = ap.parse_args()

    runs = discover([Path(r) for r in args.roots])
    runs.sort(key=lambda r: (r.family, r.circuit, -(r.gates_completed or 0)))
    write_summary_csv(runs, args.summary_csv)
    write_trajectory_csv(runs, args.trajectory_csv)

    by_fam: dict[str, int] = {}
    for r in runs:
        by_fam[r.family] = by_fam.get(r.family, 0) + 1
    print(f"Parsed {len(runs)} runs: {by_fam}")
    print(f"Summary CSV:    {args.summary_csv}")
    print(f"Trajectory CSV: {args.trajectory_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
