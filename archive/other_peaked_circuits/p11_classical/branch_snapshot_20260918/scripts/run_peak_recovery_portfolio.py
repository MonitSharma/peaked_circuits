#!/usr/bin/env python3
"""Resumable, dry-run-first local P5/P6/P8 portfolio controller.

The controller owns state and planning.  Heavy stages are intentionally explicit
and bounded; this first implementation profiles inputs and records planned MPS
rungs, leaving method execution to validated adapters.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from p12_recovery.peak.geometry import interaction_geometry  # noqa: E402
from p12_recovery.peak.campaign_runtime import CampaignBudget  # noqa: E402
from p12_recovery.peak.ensemble import read_bitstrings, reliability, summarize_samples  # noqa: E402
from p12_recovery.peak.manifest import profile  # noqa: E402
from p12_recovery.peak.mps import best_first_map  # noqa: E402
from p12_recovery.peak.qasm import parse  # noqa: E402
from p12_recovery.peak.structure import mirror_probe, weighted_backbone  # noqa: E402
from p12_recovery.peak.synthetic import control_family, statevector_to_mps  # noqa: E402
from p12_recovery.peak.watchdog import (  # noqa: E402
    child_process_count,
    memory_pressure_snapshot,
    swap_used_bytes,
    terminate_process_tree,
    tree_rss_bytes,
)

INPUTS = ROOT / "results/expert_review_p5_p6_p8_20260828/inputs"
OUT = ROOT / "results/p5_p6_p8_recovery"
FILES = {"P5": INPUTS / "P5_granite_summit.qasm", "P6": INPUTS / "P6_titan_pinnacle.qasm", "P8": INPUTS / "P8_grid_888_iswap.qasm"}
MPO_SOLVER = Path("<local-user>/code_projects/qat/peaked-mpo-solver")
MPO_PYTHON = Path("<local-user>/Code/p12-helios-recovery/.venv-p9-isolated/bin/python")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def campaign_run_id(head: str, args: argparse.Namespace) -> str:
    material = "|".join([
        head,
        *(f"{problem}:{sha256(FILES[problem])}" for problem in ("P8", "P6", "P5") if FILES[problem].exists()),
        f"threads={args.threads}", f"rss={args.rss_hard_gb}",
        f"swap={args.swap_growth_limit_gb}", f"budget={args.night_budget_hours}",
    ])
    return hashlib.sha256(material.encode()).hexdigest()[:20]


def run_stage(problem: str, bond: int, args: argparse.Namespace, outdir: Path, budget: CampaignBudget) -> dict:
    """Run exactly one local MPS stage under the process-tree RSS/wall guard."""
    output = outdir / problem / "mps" / f"D{bond}.json"
    checkpoint = outdir / problem / "mps" / f"D{bond}.checkpoint.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / "scripts/run_peak_mps.py"), "--qasm", str(FILES[problem]), "--out", str(output), "--bond", str(bond), "--checkpoint", str(checkpoint), "--wall-seconds", str(args.stage_wall_seconds)]
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = str(args.threads)
    log_path = outdir / "logs" / f"{problem}_D{bond}.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic()
        peak_rss = 0
        reason = None
        swap_start = swap_used_bytes()
        max_children = 0
        while process.poll() is None:
            peak_rss = max(peak_rss, tree_rss_bytes(process.pid))
            max_children = max(max_children, child_process_count(process.pid))
            if peak_rss > args.rss_hard_gb * 1024**3:
                reason = "rss_hard_limit"
                terminate_process_tree(process)
                break
            swap_now = swap_used_bytes()
            if swap_start is not None and swap_now is not None and swap_now - swap_start >= args.swap_growth_limit_gb * 1024**3:
                reason = "swap_growth_limit"
                terminate_process_tree(process)
                break
            if max_children > 8:
                reason = "child_process_fanout"
                terminate_process_tree(process)
                break
            if time.monotonic() >= budget.deadline:
                reason = "night_budget"
                terminate_process_tree(process)
                break
            if time.monotonic() - started >= args.stage_wall_seconds:
                reason = "wall_limit"
                terminate_process_tree(process)
                break
            time.sleep(1)
        exit_code = process.wait()
    record = {"problem": problem, "bond": bond, "command": command, "log": str(log_path), "exit_code": exit_code, "peak_process_tree_rss_bytes": peak_rss, "max_child_processes": max_children, "swap_start_bytes": swap_start, "swap_end_bytes": swap_used_bytes(), "memory_pressure_available": memory_pressure_snapshot() is not None, "runtime_s": time.monotonic() - started, "status": "ABORTED" if reason else ("COMPLETE" if exit_code == 0 else "FAILED"), "reason": reason}
    (outdir / problem / "mps" / f"D{bond}.watchdog.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def update_stage_decision(problem: str, stage: dict, outdir: Path) -> None:
    bond = stage.get("bond") or int(stage["stage"].removeprefix("MPS_D"))
    result_path = outdir / problem / "mps" / f"D{bond}.json"
    if stage.get("status") != "COMPLETE" or not result_path.exists():
        return
    result = json.loads(result_path.read_text())
    retained = float(result.get("retained_norm_proxy", 0.0))
    stage["bond"] = bond
    stage["retained_norm_proxy"] = retained
    if retained < 0.5:
        stage["status"] = "METHOD_REJECTED"
        stage["scientific_decision"] = "METHOD_REJECTED"
        stage["decision_reason"] = "retained_norm_proxy below conservative truncation diagnostic threshold"
    else:
        stage["scientific_decision"] = "PROMOTE_NEXT_RUNG"


def run_geometry_probe(outdir: Path) -> dict:
    circuit = parse(FILES["P8"])
    result = interaction_geometry(circuit)
    result.update({"stage": "GEOMETRY_PROBE", "status": "COMPLETE", "qasm_sha256": sha256(FILES["P8"])})
    target = outdir / "P8" / "geometry" / "probe.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_geometry_stage(bond: int, distance: int, args: argparse.Namespace, outdir: Path, budget: CampaignBudget) -> dict:
    output = outdir / "P8" / "geometry" / f"D{bond}_md{distance}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / "scripts/run_peak_geometry.py"), "--qasm", str(FILES["P8"]), "--out", str(output), "--max-bond", str(bond), "--cutoff", "1e-10", "--max-distance", str(distance)]
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = str(args.threads)
    log_path = outdir / "logs" / f"P8_geometry_D{bond}_md{distance}.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic()
        peak_rss = 0
        max_children = 0
        swap_start = swap_used_bytes()
        reason = None
        while process.poll() is None:
            peak_rss = max(peak_rss, tree_rss_bytes(process.pid))
            max_children = max(max_children, child_process_count(process.pid))
            if peak_rss > args.rss_hard_gb * 1024**3:
                reason = "rss_hard_limit"
                terminate_process_tree(process)
                break
            swap_now = swap_used_bytes()
            if swap_start is not None and swap_now is not None and swap_now - swap_start >= args.swap_growth_limit_gb * 1024**3:
                reason = "swap_growth_limit"
                terminate_process_tree(process)
                break
            if max_children > 8:
                reason = "child_process_fanout"
                terminate_process_tree(process)
                break
            if time.monotonic() >= budget.deadline:
                reason = "night_budget"
                terminate_process_tree(process)
                break
            if time.monotonic() - started >= min(args.stage_wall_seconds, 1800):
                reason = "wall_limit"
                terminate_process_tree(process)
                break
            time.sleep(1)
        exit_code = process.wait()
    record = {"command": command, "log": str(log_path), "exit_code": exit_code, "runtime_s": time.monotonic() - started, "peak_process_tree_rss_bytes": peak_rss, "max_child_processes": max_children, "swap_start_bytes": swap_start, "swap_end_bytes": swap_used_bytes(), "memory_pressure_available": memory_pressure_snapshot() is not None, "status": "ABORTED" if reason else ("COMPLETE" if exit_code == 0 else "FAILED"), "reason": reason}
    (outdir / "P8" / "geometry" / f"D{bond}_md{distance}.watchdog.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def mpo_calibration_pass() -> bool:
    summary = MPO_SOLVER / "runs/p9_beam_calibration_20260827/summary.json"
    if not summary.exists():
        return False
    try:
        payload = json.loads(summary.read_text())
    except json.JSONDecodeError:
        return False
    return payload.get("termination_reason") == "completed" and payload.get("matches_expected_bitstring") is True


def run_mpo_prefix(problem: str, args: argparse.Namespace, outdir: Path, budget: CampaignBudget) -> dict:
    target = outdir / problem / "mpo" / "prefix100"
    target.mkdir(parents=True, exist_ok=True)
    command = [str(MPO_PYTHON), str(ROOT / "scripts/run_p11_mpo.py"), "--solver-root", str(MPO_SOLVER), "--qasm", str(FILES[problem]), "--outdir", str(target), "--tag", f"{problem.lower()}_prefix100", "--threads", str(args.threads), "--rss-soft-gb", str(args.rss_soft_gb), "--rss-limit-gb", str(args.rss_hard_gb), "--wall-limit-s", str(min(args.stage_wall_seconds, 900)), "--samples", "0", "--decoder", "none", "--skip-sampling", "--max-bond", "64", "--cutoff", "0.005", "--max-work-gates", "100", "--abort-after-no-progress-unswap-cycles", "3", "--no-plots"]
    log_path = outdir / "logs" / f"{problem}_MPO_prefix100.log"
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = str(args.threads)
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic()
        peak_rss = 0
        max_children = 0
        swap_start = swap_used_bytes()
        reason = None
        while process.poll() is None:
            peak_rss = max(peak_rss, tree_rss_bytes(process.pid))
            max_children = max(max_children, child_process_count(process.pid))
            if peak_rss > args.rss_hard_gb * 1024**3:
                reason = "rss_hard_limit"
                terminate_process_tree(process)
                break
            swap_now = swap_used_bytes()
            if swap_start is not None and swap_now is not None and swap_now - swap_start >= args.swap_growth_limit_gb * 1024**3:
                reason = "swap_growth_limit"
                terminate_process_tree(process)
                break
            if max_children > 8:
                reason = "child_process_fanout"
                terminate_process_tree(process)
                break
            if time.monotonic() >= budget.deadline:
                reason = "night_budget"
                terminate_process_tree(process)
                break
            if time.monotonic() - started >= min(args.stage_wall_seconds, 900):
                reason = "wall_limit"
                terminate_process_tree(process)
                break
            time.sleep(1)
        exit_code = process.wait()
    record = {"command": command, "log": str(log_path), "exit_code": exit_code, "peak_process_tree_rss_bytes": peak_rss, "max_child_processes": max_children, "swap_start_bytes": swap_start, "swap_end_bytes": swap_used_bytes(), "memory_pressure_available": memory_pressure_snapshot() is not None, "runtime_s": time.monotonic() - started, "status": "ABORTED" if reason else ("COMPLETE" if exit_code == 0 else "FAILED"), "reason": reason, "solver_root": str(MPO_SOLVER), "solver_git_commit": git("-C", str(MPO_SOLVER), "rev-parse", "HEAD") if MPO_SOLVER.exists() else None}
    (target / "watchdog.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def run_mpo_full_p6(args: argparse.Namespace, outdir: Path, budget: CampaignBudget) -> dict:
    target = outdir / "P6" / "mpo" / "full_d128"
    target.mkdir(parents=True, exist_ok=True)
    command = [str(MPO_PYTHON), str(ROOT / "scripts/run_p11_mpo.py"), "--solver-root", str(MPO_SOLVER), "--qasm", str(FILES["P6"]), "--outdir", str(target), "--tag", "p6_full_d128", "--threads", str(args.threads), "--rss-soft-gb", str(args.rss_soft_gb), "--rss-limit-gb", str(args.rss_hard_gb), "--wall-limit-s", str(args.stage_wall_seconds), "--samples", "0", "--decoder", "beam", "--decoder-beam-width", "8", "--skip-sampling", "--max-bond", "128", "--cutoff", "0.005", "--abort-after-no-progress-unswap-cycles", "20", "--no-plots"]
    log_path = outdir / "logs" / "P6_MPO_full_D128.log"
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = str(args.threads)
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic()
        peak_rss = 0
        max_children = 0
        swap_start = swap_used_bytes()
        reason = None
        while process.poll() is None:
            peak_rss = max(peak_rss, tree_rss_bytes(process.pid))
            max_children = max(max_children, child_process_count(process.pid))
            if peak_rss > args.rss_hard_gb * 1024**3:
                reason = "rss_hard_limit"
                terminate_process_tree(process)
                break
            swap_now = swap_used_bytes()
            if swap_start is not None and swap_now is not None and swap_now - swap_start >= args.swap_growth_limit_gb * 1024**3:
                reason = "swap_growth_limit"
                terminate_process_tree(process)
                break
            if max_children > 8:
                reason = "child_process_fanout"
                terminate_process_tree(process)
                break
            if time.monotonic() >= budget.deadline:
                reason = "night_budget"
                terminate_process_tree(process)
                break
            if time.monotonic() - started >= args.stage_wall_seconds:
                reason = "wall_limit"
                terminate_process_tree(process)
                break
            time.sleep(1)
        exit_code = process.wait()
    record = {"command": command, "log": str(log_path), "exit_code": exit_code, "peak_process_tree_rss_bytes": peak_rss, "max_child_processes": max_children, "swap_start_bytes": swap_start, "swap_end_bytes": swap_used_bytes(), "memory_pressure_available": memory_pressure_snapshot() is not None, "runtime_s": time.monotonic() - started, "status": "ABORTED" if reason else ("COMPLETE" if exit_code == 0 else "FAILED"), "reason": reason, "solver_root": str(MPO_SOLVER), "solver_git_commit": git("-C", str(MPO_SOLVER), "rev-parse", "HEAD")}
    (target / "watchdog.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def run_structure_probe(problem: str, outdir: Path) -> dict:
    circuit = parse(FILES[problem])
    result = {"problem": problem, "stage": "STRUCTURE_PROBE", "mirror": mirror_probe(circuit), "backbone": weighted_backbone(circuit), "status": "COMPLETE", "answer_blind": True, "qasm_sha256": sha256(FILES[problem])}
    target = outdir / problem / "structure" / "probe.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_p5_reliability(outdir: Path) -> dict:
    """Summarize distinct frozen sample sources without post-hoc evaluation."""
    candidates = sorted({
        path.resolve()
        for root in (ROOT / "results/expert_review_p5_p6_p8_20260828", ROOT / "results/peaked_portal_p1_p10")
        for path in root.rglob("p5*_*/samples.tsv")
    })
    runs = []
    seen_hashes = set()
    for path in candidates:
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if source_hash in seen_hashes:
            continue
        seen_hashes.add(source_hash)
        samples = read_bitstrings(path)
        runs.append(summarize_samples(samples, method_family=path.parent.parent.name, run_id=path.parent.name, source=path))
    target = outdir / "P5" / "reliability" / "ensemble.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not runs:
        result = {"schema": "p12-p5-answer-blind-reliability-v1", "answer_blind": True, "status": "BLOCKED_MISSING_INPUT", "run_count": 0, "method_families": [], "evaluation_status": "NOT_RUN"}
    else:
        result = reliability(runs)
        result["runs"] = runs
        result["evaluation_status"] = "NOT_RUN_CANDIDATE_GENERATION_ONLY"
        result["promotion"] = "PROMOTE_JOINT_REFINEMENT" if len(result["method_families"]) >= 2 else "WAIT_INDEPENDENT_FAMILY"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    result["stage"] = "P5_ENSEMBLE_RELIABILITY"
    result["status"] = "COMPLETE" if runs else "BLOCKED_MISSING_INPUT"
    result["qasm_sha256"] = sha256(FILES["P5"])
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--execute", action="store_true", help="enable validated heavy stages; default is dry-run")
    ap.add_argument("--night-budget-hours", type=float, default=7)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--rss-soft-gb", type=float, default=20)
    ap.add_argument("--rss-hard-gb", type=float, default=24)
    ap.add_argument("--swap-growth-limit-gb", type=float, default=2)
    ap.add_argument("--cooldown-minutes", type=float, default=5)
    ap.add_argument("--stage-wall-seconds", type=float, default=6 * 3600)
    args = ap.parse_args()
    budget = CampaignBudget(time.monotonic(), args.night_budget_hours * 3600.0, args.cooldown_minutes)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "logs").mkdir(exist_ok=True)
    state_path = OUT / "CAMPAIGN_STATE.json"
    state = json.loads(state_path.read_text()) if args.resume and state_path.exists() else {"schema": "p12-peak-campaign-state-v1", "problems": {}, "nights": []}
    # An interrupted child cannot leave a live process after the controller
    # exits. Re-queue its stage; the MPS adapter will replay its checkpointed
    # prefix, while other adapters start a fresh deterministic bounded run.
    for problem_state in state.get("problems", {}).values():
        for stage in problem_state.get("stages", {}).values():
            if stage.get("status") == "RUNNING":
                stage["status"] = "PLANNED"
                stage["resume_reason"] = "controller resumed after prior interruption"
    state.update({"branch": git("branch", "--show-current"), "git_head": git("rev-parse", "HEAD"), "git_dirty": bool(git("status", "--porcelain")), "answer_blind": True, "execute": args.execute, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "command": " ".join(sys.argv)})
    state["run_id"] = campaign_run_id(state["git_head"], args)
    packages = {}
    for name in ("numpy", "scipy", "qiskit", "quimb", "cotengra", "mlx"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    (OUT / "environment.json").write_text(json.dumps({"python": sys.version, "platform": platform.platform(), "architecture": platform.machine(), "git_head": state["git_head"], "git_dirty": state["git_dirty"], "packages": packages, "threads": {key: os.environ.get(key) for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}}, indent=2) + "\n")
    (OUT / "SHA256SUMS").write_text("".join(f"{sha256(path)}  {problem}.qasm\n" for problem, path in FILES.items() if path.exists()))
    summary = {"night": len(state["nights"]) + 1, "start": state["updated_at"], "execute": args.execute, "planned_stages": [], "completed": [], "blocked": [], "aborted": [], "candidates_observed": [], "candidate_promoted": False, "human_review_required": True, "budget_seconds": budget.budget_seconds, "cooldown_minutes": args.cooldown_minutes}
    executed = False
    controls = {}
    for control_name in ("P8", "P6", "P5"):
        control = control_family(control_name, n=8)
        decoded = best_first_map(statevector_to_mps(control["statevector"], 8))
        controls[control_name] = {"passed": decoded.certified and decoded.bitstring == control["exact_top1"], "certified": decoded.certified}
    summary["synthetic_controls"] = controls
    for problem in ("P8", "P6", "P5"):
        path = FILES[problem]
        if not path.exists():
            state["problems"][problem] = {"status": "BLOCKED_MISSING_INPUT", "path": str(path)}
            summary["blocked"].append(problem)
            continue
        data = profile(path)
        data["problem"] = problem
        (OUT / f"{problem}").mkdir(exist_ok=True)
        (OUT / f"{problem}" / "manifest.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        state["problems"].setdefault(problem, {"status": "PROFILED", "stages": {}})
        stage = {"problem": problem, "stage": "STRUCTURE_PROFILE", "status": "COMPLETE", "qasm_sha256": data["sha256"]}
        state["problems"][problem]["stages"]["STRUCTURE_PROFILE"] = stage
        summary["completed"].append(f"{problem}:STRUCTURE_PROFILE")
        if problem == "P5":
            ensemble = run_p5_reliability(OUT)
            ensemble_stage = state["problems"][problem]["stages"].setdefault("ENSEMBLE_RELIABILITY", {})
            ensemble_stage.update(ensemble)
            ensemble_stage["scientific_decision"] = ensemble.get("promotion", "WAIT_INDEPENDENT_FAMILY")
            summary["completed"].append("P5:ENSEMBLE_RELIABILITY")
        for bond in ([128, 256, 512] if problem == "P8" else [64, 128, 256]):
            key = f"MPS_D{bond}"
            if key not in state["problems"][problem]["stages"]:
                planned = {"problem": problem, "stage": key, "status": "PLANNED", "resource_gates": {"rss_hard_gib": args.rss_hard_gb, "threads": args.threads}, "answer_blind": True}
                state["problems"][problem]["stages"][key] = planned
                summary["planned_stages"].append(f"{problem}:{key}")
        if problem == "P8":
            state["problems"][problem]["stages"].setdefault("GEOMETRY_PROBE", {"problem": "P8", "stage": "GEOMETRY_PROBE", "status": "PLANNED", "answer_blind": True})
            for name, bond, distance in (("GEOMETRY_D4_MD2", 4, 2), ("GEOMETRY_D4_MD3", 4, 3), ("GEOMETRY_D8_MD2", 8, 2)):
                state["problems"][problem]["stages"].setdefault(name, {"problem": "P8", "stage": name, "status": "PLANNED", "bond": bond, "max_distance": distance, "answer_blind": True, "joint_map_claim": False})
        else:
            state["problems"][problem]["stages"].setdefault("STRUCTURE_PROBE", {"problem": problem, "stage": "STRUCTURE_PROBE", "status": "PLANNED", "answer_blind": True})
            mpo_stage = state["problems"][problem]["stages"].setdefault("MPO_PREFIX", {"problem": problem, "stage": "MPO_PREFIX", "status": "PLANNED", "answer_blind": True, "joint_map_claim": False})
            mpo_solver = MPO_SOLVER / "src/p9solver/cli.py"
            if not mpo_solver.exists():
                mpo_stage.update({"status": "BLOCKED_MISSING_INPUT", "solver_path": str(mpo_solver), "reason": "local MPO solver checkout is unavailable; no remote fetch permitted"})
                summary["blocked"].append(f"{problem}:MPO_PREFIX")
            elif not mpo_calibration_pass():
                mpo_stage.update({"status": "METHOD_REJECTED", "solver_path": str(mpo_solver), "reason": "P9 calibration artifact does not pass the known-control gate"})
                summary["blocked"].append(f"{problem}:MPO_PREFIX")
            else:
                mpo_stage.update({"status": "PLANNED", "solver_path": str(mpo_solver), "solver_git_commit": git("-C", str(MPO_SOLVER), "rev-parse", "HEAD"), "p9_calibration_passed": True})
                existing_candidates = [
                    OUT / problem / "mpo" / "prefix100" / f"{problem.lower()}_prefix100" / "summary.json",
                    OUT / problem / "mpo_prefix" / "p6_prefix100_abs" / "summary.json",
                ]
                existing = next((candidate for candidate in existing_candidates if candidate.exists()), None)
                if existing is not None:
                    mpo_stage.update({"status": "COMPLETE", "summary_path": str(existing), "scientific_decision": "PREFIX_COMPATIBILITY_ONLY"})
            if problem == "P6":
                state["problems"][problem]["stages"].setdefault("MPO_FULL_D128", {"problem": "P6", "stage": "MPO_FULL_D128", "status": "PLANNED", "bond": 128, "cutoff": 0.005, "answer_blind": True, "joint_map_claim": False})
        for stage in state["problems"][problem]["stages"].values():
            if stage.get("stage", "").startswith("MPS_D"):
                update_stage_decision(problem, stage, OUT)
    if args.execute and all(item["passed"] for item in controls.values()):
        # One heavy process only. Controls are represented by the tested local
        # MPS fixture; target stages remain answer-blind and independently gated.
        def eligible(required_seconds: float) -> bool:
            if budget.can_start(time.monotonic(), required_seconds):
                return True
            summary["budget_exhausted"] = True
            summary["blocked"].append("NIGHT_BUDGET_INSUFFICIENT")
            return False

        def record_cooldown(stage_started: float) -> None:
            seconds = budget.cooldown_seconds(time.monotonic() - stage_started)
            if seconds:
                summary["cooldown_applied_seconds"] = seconds
                time.sleep(min(seconds, budget.remaining(time.monotonic())))

        for problem in ("P8", "P6", "P5"):
            stages = state["problems"].get(problem, {}).get("stages", {})
            if problem in ("P6", "P5") and stages.get("STRUCTURE_PROBE", {}).get("status") == "PLANNED":
                if not eligible(60.0):
                    break
                stage_started = time.monotonic()
                result = run_structure_probe(problem, OUT)
                stages["STRUCTURE_PROBE"].update(result, scientific_decision="SELECT_METHOD_FROM_STRUCTURE")
                summary["completed"].append(f"{problem}:STRUCTURE_PROBE")
                executed = True
                record_cooldown(stage_started)
                break
            if problem in ("P6", "P5") and stages.get("STRUCTURE_PROBE", {}).get("status") == "COMPLETE" and stages.get("MPS_D64", {}).get("scientific_decision") == "METHOD_REJECTED" and stages.get("MPO_PREFIX", {}).get("status") == "PLANNED":
                if not eligible(min(args.stage_wall_seconds, 900.0)):
                    break
                stage_started = time.monotonic()
                result = run_mpo_prefix(problem, args, OUT, budget)
                stages["MPO_PREFIX"].update(result, scientific_decision="PREFIX_COMPATIBILITY_ONLY" if result["status"] == "COMPLETE" else "MPO_PREFIX_ABORTED")
                summary["completed" if result["status"] == "COMPLETE" else "blocked"].append(f"{problem}:MPO_PREFIX")
                executed = True
                record_cooldown(stage_started)
                break
            if problem == "P6" and stages.get("MPO_PREFIX", {}).get("status") == "COMPLETE" and stages.get("MPO_FULL_D128", {}).get("status") == "PLANNED":
                if not eligible(args.stage_wall_seconds):
                    break
                stage_started = time.monotonic()
                result = run_mpo_full_p6(args, OUT, budget)
                stages["MPO_FULL_D128"].update(result, scientific_decision="FULL_MPO_DIAGNOSTIC" if result["status"] == "COMPLETE" else "MPO_FULL_ABORTED")
                summary["completed" if result["status"] == "COMPLETE" else "blocked"].append("P6:MPO_FULL_D128")
                executed = True
                record_cooldown(stage_started)
                break
            if problem == "P8" and stages.get("MPS_D128", {}).get("scientific_decision") == "METHOD_REJECTED" and stages.get("GEOMETRY_PROBE", {}).get("status") == "PLANNED":
                if not eligible(60.0):
                    break
                stage_started = time.monotonic()
                result = run_geometry_probe(OUT)
                stages["GEOMETRY_PROBE"].update(result, scientific_decision="METHOD_STOP_GEOMETRY_DIAGNOSTIC_ONLY")
                summary["completed"].append("P8:GEOMETRY_PROBE")
                executed = True
                record_cooldown(stage_started)
                break
            if problem == "P8" and stages.get("MPS_D128", {}).get("scientific_decision") == "METHOD_REJECTED" and stages.get("GEOMETRY_PROBE", {}).get("status") == "COMPLETE":
                geometry_names = ["GEOMETRY_D4_MD2", "GEOMETRY_D4_MD3", "GEOMETRY_D8_MD2"]
                for index, name in enumerate(geometry_names):
                    stage = stages.get(name, {})
                    if stage.get("status") != "PLANNED":
                        continue
                    if index and stages[geometry_names[index - 1]].get("scientific_decision") != "PROMOTE_NEXT_GEOMETRY_RUNG":
                        continue
                    if not eligible(min(args.stage_wall_seconds, 1800.0)):
                        break
                    stage_started = time.monotonic()
                    result = run_geometry_stage(stage["bond"], stage["max_distance"], args, OUT, budget)
                    stage.update(result)
                    output = OUT / "P8" / "geometry" / f"D{stage['bond']}_md{stage['max_distance']}.json"
                    if result["status"] == "COMPLETE" and output.exists():
                        payload = json.loads(output.read_text())
                        stage["product_marginal_diagnostic"] = payload.get("product_marginal_diagnostic")
                        if index == 0:
                            stage["scientific_decision"] = "PROMOTE_NEXT_GEOMETRY_RUNG"
                        else:
                            previous = stages[geometry_names[index - 1]].get("product_marginal_diagnostic")
                            stage["scientific_decision"] = "PROMOTE_NEXT_GEOMETRY_RUNG" if previous == stage["product_marginal_diagnostic"] else "GEOMETRY_UNSTABLE"
                    summary["completed" if result["status"] == "COMPLETE" else "blocked"].append(f"P8:{name}")
                    executed = True
                    record_cooldown(stage_started)
                    break
                if executed:
                    break
            rung_names = sorted(
                (name for name in stages if name.startswith("MPS_D")),
                key=lambda name: int(name.removeprefix("MPS_D")),
            )
            next_stage = None
            for position, name in enumerate(rung_names):
                if stages[name]["status"] != "PLANNED":
                    continue
                prior = rung_names[:position]
                if all(stages[item].get("scientific_decision") == "PROMOTE_NEXT_RUNG" for item in prior):
                    next_stage = name
                    break
            if not next_stage:
                continue
            bond = int(next_stage.removeprefix("MPS_D"))
            if not eligible(args.stage_wall_seconds):
                break
            stages[next_stage]["status"] = "RUNNING"
            stage_started = time.monotonic()
            result = run_stage(problem, bond, args, OUT, budget)
            stages[next_stage].update(result)
            if result["status"] == "COMPLETE":
                summary["completed"].append(f"{problem}:{next_stage}")
            else:
                summary["blocked"].append(f"{problem}:{next_stage}:{result.get('reason', result['status'])}")
            executed = True
            record_cooldown(stage_started)
            break
    elif args.execute:
        summary["blocked"].append("CONTROLS_NOT_PASSED")
    state["nights"].append(summary)
    stage_records = []
    for problem in ("P8", "P6", "P5"):
        for stage in state["problems"].get(problem, {}).get("stages", {}).values():
            if stage.get("bond") and stage.get("status") in {"COMPLETE", "METHOD_REJECTED", "ABORTED", "FAILED"}:
                stage_records.append(stage)
    summary["total_heavy_compute_time_s"] = sum(float(item.get("runtime_s", 0)) for item in stage_records)
    summary.setdefault("budget_exhausted", time.monotonic() >= budget.deadline)
    summary["budget_elapsed_s"] = time.monotonic() - budget.started_monotonic
    summary["max_process_tree_rss_bytes"] = max((int(item.get("peak_process_tree_rss_bytes", 0)) for item in stage_records), default=0)
    summary["next_recommended_command"] = "PYTHONPATH=src .venv/bin/python scripts/run_peak_recovery_portfolio.py --resume"
    summary["next_reason"] = "Initial MPS rungs and P8 geometry probes stopped scientifically; MPO prefix compatibility is gated by the validated local P9 solver calibration."
    research_path = OUT / "RESEARCH_STATE.json"
    research = json.loads(research_path.read_text()) if research_path.exists() else {}
    research.setdefault("result_classes", ["BLOCKED_MISSING_INPUT", "CONTROL_FAILED", "METHOD_REJECTED", "METHOD_RESOURCE_NO_GO", "UNCONVERGED", "PROMISING_CANDIDATE_FAMILY", "STRONG_PROVISIONAL_CANDIDATE", "CROSS_METHOD_CONVERGED_CANDIDATE", "CURRENT_METHODS_EXHAUSTED"])
    if research.get("candidate") is None:
        freeze = OUT / "P5" / "freezes" / "P5_CANDIDATE_FREEZE.json"
        if freeze.exists():
            frozen = json.loads(freeze.read_text())
            research["candidate"] = {"problem": "P5", "status": "PARTIAL_SIGNAL", "freeze": str(freeze.relative_to(OUT)), "reliability": "P5/reliability/ensemble.json", "evaluation_status": frozen.get("evaluation_status", "NOT_RUN")}
        else:
            research["candidate"] = None
    research.update({"p9_bit_order_validated": True, "p9_mpo_gate_passed": mpo_calibration_pass(), "target_answer_accessed": False, "updated_at": state["updated_at"]})
    research_path.write_text(json.dumps(research, indent=2) + "\n")
    (OUT / "CAMPAIGN_STATE.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    for problem in ("P8", "P6", "P5"):
        (OUT / problem / "STATE.json").write_text(json.dumps(state["problems"].get(problem, {}), indent=2, sort_keys=True) + "\n")
    (OUT / "NIGHT_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    markdown = [f"# P5/P6/P8 Night {summary['night']} Summary", "", f"- Execute mode: `{args.execute}`", f"- Answer-blind: `{state['answer_blind']}`", f"- Candidate promoted: `{summary['candidate_promoted']}`", "", "## Stage accounting", ""]
    markdown.extend(f"- `{item}`" for item in summary["completed"])
    markdown.extend(f"- blocked: `{item}`" for item in summary["blocked"])
    markdown.append("")
    markdown.append("No target answer is stored or asserted; all candidates remain subject to independent cross-method evidence.")
    (OUT / "NIGHT_SUMMARY.md").write_text("\n".join(markdown) + "\n")
    print(json.dumps(summary, indent=2))
    if args.execute:
        print("Executed one bounded local stage." if executed else "No eligible heavy stage remained.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
