#!/usr/bin/env python3
"""Resumable, P9-gated HPC orchestrator; never runs P11 on non-Linux hosts."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from pathlib import Path


P9 = "data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm"
P11 = "data/canonical/peaked_circuit_P11_Hqap_98x1999.qasm"
P9_WORK_GATES = 1885
P9_QUBITS = 56


def read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def valid_p9_calibration(summary_path: Path) -> bool:
    """Require a complete, independently checkable P9 calibration control."""
    summary = read_json(summary_path)
    if summary is None:
        return False
    permutation = summary.get("measurement_perm")
    samples_path = summary.get("samples_path")
    return (
        summary.get("run_status") == "complete"
        and summary.get("termination_reason") == "completed"
        and summary.get("partial") is False
        and summary.get("num_qubits") == P9_QUBITS
        and summary.get("consolidated_ops", {}).get("unitary") == P9_WORK_GATES
        and summary.get("last_work_consumed") == P9_WORK_GATES
        and summary.get("samples") == 1000
        and isinstance(permutation, list)
        and sorted(permutation) == list(range(P9_QUBITS))
        and isinstance(samples_path, str)
        and Path(samples_path).is_file()
        and summary.get("matches_expected_bitstring") is True
        and summary.get("predicted_bitstring") == summary.get("expected_bitstring")
    )


def valid_p9_manifest(stage_dir: Path) -> bool:
    manifests = list(stage_dir.glob("*.p9_manifest.json"))
    if len(manifests) != 1:
        return False
    manifest = read_json(manifests[0])
    if manifest is None:
        return False
    command = [str(item) for item in manifest.get("command", [])]
    return (
        any(Path(P9).name in item for item in command)
        and "--expected-bitstring" in command
        and command[command.index("--expected-bitstring") + 1] != ""
    )


def valid_launcher_record(stage_dir: Path, *, qasm_name: str) -> bool:
    record = read_json(stage_dir / "launcher_record.json")
    manifest = read_json(stage_dir / "launcher_manifest.json")
    if record is None or manifest is None:
        return False
    command = [str(item) for item in manifest.get("command", [])]
    try:
        expected_index = command.index("--expected-bitstring")
    except ValueError:
        return False
    return (
        record.get("termination_reason") == "completed"
        and isinstance(record.get("wall_time_s"), (int, float))
        and record["wall_time_s"] >= 0
        and isinstance(record.get("peak_process_tree_rss_gb"), (int, float))
        and record["peak_process_tree_rss_gb"] >= 0
        and any(qasm_name in item for item in command)
        and expected_index + 1 < len(command)
        and command[expected_index + 1] == ""
    )


def valid_p11_stage(stage_dir: Path, *, horizon: int) -> bool:
    summaries = list(stage_dir.rglob("summary.json"))
    stats_files = list(stage_dir.rglob("stats.json"))
    if len(summaries) != 1 or len(stats_files) != 1 or not valid_launcher_record(stage_dir, qasm_name=Path(P11).name):
        return False
    summary = read_json(summaries[0])
    if summary is None:
        return False
    return (
        summary.get("run_status") == "complete"
        and summary.get("termination_reason") == "completed"
        and summary.get("partial") is False
        and summary.get("last_work_consumed") == horizon
        and summary.get("qasm", "").endswith(Path(P11).name)
        and summary.get("expected_bitstring", "") == ""
        and summary.get("parameters", {}).get("expected_bitstring", "") == ""
    )


P11_FIXED_HORIZON = 250
P11_SUSTAINED_HORIZON = 350
P11_H1_MIN_CAPACITY_RATIO = 2.0
P11_H1_MIN_SATURATION_REDUCTION = 0.10

def read_json_value(path: Path):
    try: return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return None

def p11_metrics(stage_dir: Path) -> dict | None:
    summaries=list(stage_dir.rglob("summary.json")); stats_files=list(stage_dir.rglob("stats.json"))
    if len(summaries)!=1 or len(stats_files)!=1: return None
    summary=read_json(summaries[0]); stats=read_json_value(stats_files[0]); launcher=read_json(stage_dir/"launcher_record.json")
    if summary is None or launcher is None or not isinstance(stats,list) or not stats: return None
    bonds=[float(r["max_bond"]) for r in stats if isinstance(r,dict) and isinstance(r.get("max_bond"),(int,float))]
    times=[float(r["time"]) for r in stats if isinstance(r,dict) and isinstance(r.get("time"),(int,float))]
    limit=float(summary.get("parameters",{}).get("max_bond",0) or 0)
    sat=sum(1 for b in bonds if limit and b>=limit)
    return {"work":summary.get("last_work_consumed"),"partial":summary.get("partial"),"peak_bond":float(summary.get("peak_max_bond",max(bonds,default=0)) or 0),"peak_total_elems":float(summary.get("peak_total_elems",0) or 0),"stats_rows":len(stats),"wall_time_s":max(times,default=0.0),"saturation_fraction":sat/max(len(bonds),1),"rss_gb":float(launcher.get("peak_process_tree_rss_gb",0) or 0),"rss_limit_gb":float(summary.get("parameters",{}).get("rss_limit_gb",0) or 0)}

def valid_m3_failure_baseline(path: Path) -> bool:
    v=read_json(path)
    return v is not None and isinstance(v.get("horizon"),int) and isinstance(v.get("useful_work"),(int,float)) and isinstance(v.get("rss_gb"),(int,float)) and v.get("useful_work",0)>=0 and v.get("rss_gb",0)>0

def high_bond_gate(campaign: Path) -> tuple[bool,dict]:
    base=p11_metrics(campaign/"high_bond"/"D512")
    ev={"baseline":base,"candidates":{},"thresholds":{"capacity_ratio":P11_H1_MIN_CAPACITY_RATIO,"saturation_reduction":P11_H1_MIN_SATURATION_REDUCTION}}
    if base is None or base.get("work")!=P11_FIXED_HORIZON or base.get("partial") is not False: return False,ev
    ok=False
    for bond in (1024,2048,4096):
        m=p11_metrics(campaign/"high_bond"/f"D{bond}"); ev["candidates"][str(bond)]=m
        if m is None or m.get("work")!=P11_FIXED_HORIZON or m.get("partial") is not False: continue
        cr=m["peak_bond"]/max(base["peak_bond"],1.0); sr=(base["saturation_fraction"]-m["saturation_fraction"])/max(base["saturation_fraction"],1e-12)
        ev["candidates"][str(bond)].update({"capacity_ratio":cr,"saturation_reduction":sr})
        ok = ok or (cr>=P11_H1_MIN_CAPACITY_RATIO and sr>=P11_H1_MIN_SATURATION_REDUCTION)
    return ok,ev

def sustained_p11_gate(campaign: Path, stage_name: str) -> tuple[bool,dict]:
    m=p11_metrics(campaign/"beam"/stage_name); bp=campaign.parent/"M3_FAILURE_BASELINE.json"
    base=read_json(bp) if valid_m3_failure_baseline(bp) else None
    ev={"metrics":m,"m3_failure_baseline":base,"required_work":P11_SUSTAINED_HORIZON}
    if m is None or m.get("partial") is not False or m.get("work",0)<P11_SUSTAINED_HORIZON or m.get("rss_gb",0)<=0 or m.get("rss_limit_gb",0)<=0 or m.get("rss_gb")>m.get("rss_limit_gb") or base is None: return False,ev
    return m["work"]>base["useful_work"],ev

def save(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def run_stage(state: dict, state_path: Path, name: str, command: list[str], *, dry_run: bool) -> bool:
    record = {"status": "RUNNING", "start": time.time(), "command": command}
    state["stages"][name] = record
    save(state_path, state)
    if dry_run:
        record.update({"status": "DRY_RUN", "exit_code": 0, "end": time.time()})
        save(state_path, state)
        return True
    with (state_path.parent / f"{name}.log").open("w") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=state["repo_root"])
    record.update({"status": "PASS" if result.returncode == 0 else "FAIL", "exit_code": result.returncode, "end": time.time()})
    save(state_path, state)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if platform.system() != "Linux" and not args.dry_run:
        raise SystemExit("The real HPC campaign is Linux-only; use --dry-run for Mac orchestration smoke tests.")
    campaign = args.campaign_dir.resolve()
    campaign.mkdir(parents=True, exist_ok=True)
    state_path = campaign / "RUN_STATE.json"
    if args.resume and state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = {"schema": "p11-hpc-campaign-v1", "repo_root": str(root), "campaign_dir": str(campaign), "p11_blind": True, "stages": {}, "next_stage": "PREFLIGHT"}
        save(state_path, state)
    env_python = root / ".venv-hpc/bin/python"
    solver_root = root / "external/peaked-mpo-solver"
    def completed(stage: str) -> bool:
        record = state.get("stages", {}).get(stage, {})
        if record.get("status") == "DRY_RUN":
            return True
        if record.get("status") != "PASS":
            return False
        if stage.startswith("P9_NUMA_"):
            label = stage.rsplit("_", 1)[1]
            return valid_p9_calibration(campaign / "p9" / label / f"p9_{label}" / "summary.json")
        if stage == "P9_REAL_BEAM_W8_D2":
            summaries = list((campaign / "p9_real_beam").rglob("summary.json"))
            return len(summaries) == 1 and valid_p9_calibration(summaries[0]) and valid_p9_manifest(campaign / "p9_real_beam")
        if stage.startswith("P11_HIGH_BOND_D"):
            return valid_p11_stage(campaign / "high_bond" / stage.removeprefix("P11_HIGH_BOND_"), horizon=250)
        if stage.startswith("P11_BEAM_"):
            return valid_p11_stage(campaign / "beam" / stage.removeprefix("P11_BEAM_"), horizon=int(stage.rsplit("_", 1)[1]))
        return True

    running = [name for name, record in state.get("stages", {}).items() if record.get("status") == "RUNNING"]
    if running:
        state["status"] = "WAITING_FOR_STAGE_COMPLETION"
        state["active_stages"] = running
        save(state_path, state)
        return 0
    if not completed("PREFLIGHT"):
        if not run_stage(state, state_path, "PREFLIGHT", ["bash", str(root / "hpc/preflight.sh")], dry_run=args.dry_run): return 2
    profiles = (("A", "one_node", 18, 120), ("B", "two_nodes", 36, 240), ("C", "four_nodes", 72, 450))
    for label, mode, threads, rss in profiles:
        stage = f"P9_NUMA_{label}"
        command = ["bash", str(root / "hpc/run_numa_job.sh"), str(env_python), str(root / "scripts/run_p9_hpc_calibration.py"), "--qasm", str(root / P9), "--solver-root", str(solver_root), "--outdir", str(campaign / "p9" / label), "--tag", f"p9_{label}", "--threads", str(threads), "--max-bond", "512", "--cutoff", "0.0006"]
        if not completed(stage) and not run_stage(state, state_path, stage, command, dry_run=args.dry_run): return 3
    state["next_stage"] = "H0_DECISION"
    state["h0_policy"] = "select_profile_from_measured_p9_summary; stop if no 56/56 result"
    if state.get("selected_profile") is None:
        evidence = []
        for label, mode, threads, rss in profiles:
            summaries = list((campaign / "p9" / label).rglob("summary.json"))
            for summary_path in summaries:
                try:
                    summary = json.loads(summary_path.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                if valid_p9_calibration(summary_path):
                    evidence.append({"label": label, "mode": mode, "threads": threads, "rss_limit_gb": rss, "wall_time_s": summary.get("compress_time_s", float("inf")), "summary": str(summary_path)})
        if args.dry_run:
            evidence = [{"label": "A", "mode": "one_node", "threads": 18, "rss_limit_gb": 120, "wall_time_s": None, "summary": "dry-run"}]
        if evidence:
            state["selected_profile"] = min(evidence, key=lambda item: item["wall_time_s"] if item["wall_time_s"] is not None else float("inf"))
            state["h0"] = "PASS"
        elif not args.dry_run:
            state["h0"] = "FAIL_P9_DID_NOT_REPRODUCE_56_OF_56"
            state["status"] = "HPC_ENVIRONMENT_INVALID"
            save(state_path, state)
            return 5
    save(state_path, state)
    # The orchestrator does not guess a profile from incomplete logs. A later
    # resume after H0 records the selected profile explicitly.
    if state.get("selected_profile") is None:
        state["status"] = "WAITING_FOR_H0_PROFILE_SELECTION"
        save(state_path, state)
        return 0
    selected = state["selected_profile"]
    # D512 is the preregistered lower-bond comparator for H1.
    for bond in (512, 1024, 2048, 4096):
        stage = f"P11_HIGH_BOND_D{bond}"
        command = ["bash", str(root / "hpc/run_numa_job.sh"), str(env_python), str(root / "scripts/run_p11_mpo.py"), "--solver-root", str(solver_root), "--qasm", str(root / P11), "--outdir", str(campaign / "high_bond" / f"D{bond}"), "--tag", f"p11_D{bond}", "--threads", str(selected["threads"]), "--rss-limit-gb", str(selected["rss_limit_gb"]), "--max-bond", str(bond), "--cutoff", "0.0006", "--max-work-gates", "250", "--expected-bitstring", ""]
        if not completed(stage) and not run_stage(state, state_path, stage, command, dry_run=args.dry_run): return 4
    high_bond_evidence = all(
        valid_p11_stage(campaign / "high_bond" / f"D{bond}", horizon=P11_FIXED_HORIZON)
        for bond in (512, 1024, 2048, 4096)
    )
    h1_pass, h1_metrics = (True, {"dry_run": True}) if args.dry_run else high_bond_gate(campaign)
    state["h1_metrics"] = h1_metrics
    if not args.dry_run and (not high_bond_evidence or not h1_pass):
        state["h1"] = "FAIL_HIGH_BOND_QUANTITATIVE_IMPROVEMENT"
        state["status"] = "P11_HPC_NO_GO"
        save(state_path, state)
        return 0
    state["h1"] = "PASS_HIGH_BOND_QUANTITATIVE_IMPROVEMENT"
    state["next_stage"] = "P9_REAL_BEAM"
    save(state_path, state)
    beam_stage = "P9_REAL_BEAM_W8_D2"
    beam_command = ["bash", str(root / "hpc/run_numa_job.sh"), str(env_python), str(root / "scripts/run_p9_hpc_calibration.py"), "--qasm", str(root / P9), "--solver-root", str(solver_root), "--outdir", str(campaign / "p9_real_beam"), "--tag", "p9_real_beam_w8_d2", "--threads", str(selected["threads"]), "--max-bond", "512", "--cutoff", "0.0006", "--unswap-select-mode", "pair_lookahead", "--unswap-pair-lookahead-limit", "8"]
    if not completed(beam_stage) and not run_stage(state, state_path, beam_stage, beam_command, dry_run=args.dry_run): return 6
    beam_summaries = list((campaign / "p9_real_beam").rglob("summary.json"))
    beam_pass = args.dry_run or (
        len(beam_summaries) == 1
        and valid_p9_calibration(beam_summaries[0])
        and valid_p9_manifest(campaign / "p9_real_beam")
        and read_json(beam_summaries[0]).get("parameters", {}).get("unswap_select_mode") == "pair_lookahead"
    )
    state["h2"] = "PASS_REAL_MPO_BEAM_P9_CALIBRATION" if beam_pass else "REAL_MPO_BEAM_P9_NO_GO"
    state["h2_claim"] = "P9 calibration only; no beam-vs-greedy claim is made."
    if not beam_pass:
        state["status"] = "BEAM_MPO_P9_NO_GO"
        state["next_stage"] = "FINAL_REPORT"
        save(state_path, state)
        return 0
    for horizon in (350, 500, 1000, 1984):
        stage = f"P11_BEAM_{horizon}"
        command = ["bash", str(root / "hpc/run_numa_job.sh"), str(env_python), str(root / "scripts/run_p11_mpo.py"), "--solver-root", str(solver_root), "--qasm", str(root / P11), "--outdir", str(campaign / "beam" / str(horizon)), "--tag", f"p11_beam_{horizon}", "--threads", str(selected["threads"]), "--rss-limit-gb", str(selected["rss_limit_gb"]), "--max-bond", "4096", "--cutoff", "0.0006", "--max-work-gates", str(horizon), "--unswap-select-mode", "pair_lookahead", "--unswap-pair-lookahead-limit", "8", "--expected-bitstring", ""]
        if not completed(stage) and not run_stage(state, state_path, stage, command, dry_run=args.dry_run):
            state["status"] = "P11_HPC_NO_GO"
            save(state_path, state)
            return 0
        if not args.dry_run and not valid_p11_stage(campaign / "beam" / str(horizon), horizon=horizon):
            state["h3"] = f"FAIL_P11_BEAM_{horizon}_INVALID"
            state["status"] = "P11_HPC_NO_GO"
            save(state_path, state)
            return 0
        if horizon == P11_SUSTAINED_HORIZON:
            h3_pass, h3_metrics = (True, {"dry_run": True}) if args.dry_run else sustained_p11_gate(campaign, "350")
            state["h3_metrics"] = h3_metrics
            if not args.dry_run and not h3_pass:
                state["h3"] = "FAIL_P11_SUSTAINED_PROGRESS"
                state["status"] = "P11_HPC_NO_GO"
                save(state_path, state)
                return 0
            state["h3"] = "PASS_P11_SUSTAINED_PROGRESS"
    state["h4"] = "PASS_P11_FULL_HORIZON_VALIDATED"
    state["status"] = "P11_CLASSICAL_SUCCESS"
    state["next_stage"] = "FINAL_REPORT"
    save(state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
