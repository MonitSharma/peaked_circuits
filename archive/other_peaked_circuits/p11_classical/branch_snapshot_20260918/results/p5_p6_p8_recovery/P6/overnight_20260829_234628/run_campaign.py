#!/usr/bin/env python3
"""Resumable, serialized P6 MPO campaign controller."""
import hashlib, json, os, subprocess, sys, time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path('/Users/monitsharma/Code/p12-helios-recovery')
CAMPAIGN = ROOT / 'results/p5_p6_p8_recovery/P6/overnight_20260829_234628'
QASM = ROOT / 'results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm'
SOLVER = Path('/Users/monitsharma/code_projects/qat/peaked-mpo-solver')
PYTHON = '/Users/monitsharma/.conda/envs/p9-openblas/bin/python'
EXPECTED_SHA = '206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4'
TOTAL_GATES = 2593
STATE = CAMPAIGN / 'CAMPAIGN_STATE.json'
LOG = CAMPAIGN / 'CAMPAIGN_LOG.md'

def now(): return datetime.now(timezone.utc).isoformat()
def heavy():
    out = subprocess.check_output(['ps','-Ao','pid=,command='], text=True)
    return [x.strip() for x in out.splitlines() if ('python -m p9solver.cli' in x or 'scripts/run_p11_mpo.py' in x)]
def write_state(**kw):
    old = json.loads(STATE.read_text()) if STATE.exists() else {}
    old.update(kw); STATE.write_text(json.dumps(old, indent=2) + '\n')
def log(s):
    with LOG.open('a') as f: f.write(f'\n- {now()} {s}\n')
def gates(outdir):
    stats = next(outdir.glob('*/stats.json'), None)
    if not stats: return 0
    try:
        rows = json.loads(stats.read_text())
        return max([int(r.get('u_consumed_total', 0)) for r in rows] + [0])
    except Exception: return 0
KNOWN = {
    'A1':'11001011010111011010100010111011101100110100101111100001110110',
    'A2':'11011011110101011010100010111011001100010100000011100001110010',
    'A3':'10011111010101011010100010111010001100010100101011101001110010',
    'A4':'11010000011001111100000010011000110100111101100000111100011010',
    'A5':'11100011000101111111011101011001110100110110000011010010010010',
}
def candidates(summary):
    out=[]
    for key in ('predicted_bitstring','decoded_bitstring','best_bitstring'):
        v=summary.get(key)
        if isinstance(v,str) and len(v)==62 and set(v)<=set('01'): out.append(v)
    for key in ('decoder_topk','top_permuted_samples'):
        v=summary.get(key)
        if isinstance(v,list):
            for item in v:
                b = item if isinstance(item,str) else (item.get('bitstring') or item.get('bits')) if isinstance(item,dict) else None
                if isinstance(b,str) and len(b)==62 and set(b)<=set('01'): out.append(b)
    return list(dict.fromkeys(out))
def overlaps(bits):
    return [{'reference':k,'matching_positions':sum(a==b for a,b in zip(bits,v)),'length':len(bits)} for k,v in KNOWN.items()]
def run(name, cutoff, mode=None, wall=14400, seed=123):
    out = CAMPAIGN / name
    args = [PYTHON, str(ROOT/'scripts/run_p11_mpo.py'), '--solver-root', str(SOLVER), '--qasm', str(QASM), '--outdir', str(out), '--tag', name, '--threads','3','--rss-soft-gb','20','--rss-limit-gb','24','--wall-limit-s',str(wall),'--samples','1000','--decoder','beam','--decoder-beam-width','8','--max-bond','512','--cutoff',str(cutoff),'--unswap-threshold','500000','--sabre-trials','90','--post-sabre-trials','50','--seed',str(seed),'--route-candidates','4','--route-score','bond_profile','--route-score-lookahead','8','--abort-after-no-progress-unswap-cycles','60','--no-plots']
    if mode: args += ['--unswap-select-mode', mode, '--unswap-pair-lookahead-limit','8']
    write_state(current_stage=name, exact_command=args, process_id=None, start_timestamp=now(), end_timestamp=None, exit_status=None, termination_reason=None, work_gates_processed=0, last_progress_time=now(), maximum_bond=None, peak_tensor_elements=None, peak_rss=None, output_paths=[str(out)], completed_all_gates=False, candidate_assessment='not_assessed')
    log(f'Launching {name}: `{" ".join(args)}`')
    env = os.environ.copy()
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): env[k]='3'
    with (CAMPAIGN/(name+'.controller.log')).open('w') as lf:
        p = subprocess.Popen(['caffeinate','-i','nice','-n','10',*args], cwd=SOLVER, env=env, stdout=lf, stderr=subprocess.STDOUT)
        write_state(process_id=p.pid)
        ret = p.wait()
    rec = out/'launcher_record.json'
    record = json.loads(rec.read_text()) if rec.exists() else {}
    summary = next(out.glob('*/summary.json'), None)
    sd = json.loads(summary.read_text()) if summary else {}
    n = gates(out)
    complete = sd.get('run_status') == 'complete' and n == TOTAL_GATES
    write_state(end_timestamp=now(), exit_status=ret, termination_reason=record.get('termination_reason'), work_gates_processed=n, completed_all_gates=complete, maximum_bond=sd.get('peak_max_bond'), peak_tensor_elements=sd.get('peak_total_elems'), peak_rss=record.get('peak_process_tree_rss_gb'), output_paths=[str(out)])
    log(f'Finished {name}: exit={ret}, gates={n}, complete={complete}, reason={record.get("termination_reason")}')
    return complete, sd
def main():
    if hashlib.sha256(QASM.read_bytes()).hexdigest() != EXPECTED_SHA: raise SystemExit('QASM SHA mismatch; refusing to run')
    CAMPAIGN.mkdir(parents=True, exist_ok=True)
    if not STATE.exists():
        STATE.write_text(json.dumps({'campaign_start_time': now(), 'deadline': None, 'current_stage':'waiting_for_idle', 'qasm_sha256':EXPECTED_SHA, 'total_work_gates':TOTAL_GATES}, indent=2)+'\n')
        LOG.write_text('# P6 overnight campaign\n')
    st = json.loads(STATE.read_text())
    deadline = datetime.fromisoformat(st['deadline']) if st.get('deadline') else None
    if deadline and datetime.now(timezone.utc) >= deadline: return
    idle = 0
    while idle < 2:
        if heavy():
            idle = 0; write_state(current_stage='waiting_for_idle', last_idle_check=now(), idle_checks=idle); log('Heavy solver active; waiting 300 seconds.')
        else:
            idle += 1; write_state(current_stage='idle_check', last_idle_check=now(), idle_checks=idle); log(f'Idle check {idle}/2 passed.')
        if idle < 2: time.sleep(300)
    deadline = datetime.now(timezone.utc) + timedelta(hours=12)
    write_state(campaign_machine_free_time=now(), deadline=deadline.isoformat(), current_stage='stage_a')
    stages = [('stage_a_p6_d512_cut1e3','0.001',None,14400),('stage_b_p6_pair_cut6e4','0.0006','pair_lookahead',14400),('stage_c_p6_pair_cut1e3','0.001','pair_lookahead',10800)]
    completed = {}
    for name, cut, mode, wall in stages:
        if datetime.now(timezone.utc) >= deadline: break
        if heavy(): raise SystemExit('Unexpected heavy solver appeared before launch')
        completed[name], _ = run(name, cut, mode, min(wall, int((deadline-datetime.now(timezone.utc)).total_seconds())))
        if completed[name]: break
    if not any(completed.values()) and datetime.now(timezone.utc) < deadline:
        # Intermediate ladder; pair-lookahead is selected only because it is the new P6-specific mode.
        for cut in ('0.00125','0.0015','0.00175'):
            if datetime.now(timezone.utc) >= deadline: break
            name = 'stage_d_p6_pair_cut' + cut.replace('.','p')
            completed[name], _ = run(name, cut, 'pair_lookahead', min(10800, int((deadline-datetime.now(timezone.utc)).total_seconds())))
            if completed[name]: break
    assess = {'terminal_campaign_status':'NONCONVERGED','stages':completed,'best_completed_gate_count':0,'credible_candidate':None,'overlap_validation_table':[],'candidate_evidence':[]}
    for d in CAMPAIGN.glob('stage_*'):
        s = next(d.glob('*/summary.json'),None)
        if s:
            x=json.loads(s.read_text()); n=gates(d); assess['best_completed_gate_count']=max(assess['best_completed_gate_count'], n)
            for bits in candidates(x):
                assess['candidate_evidence'].append({'stage':d.name,'bitstring':bits,'overlap_validation':overlaps(bits),'sample_peak_fraction':x.get('sample_peak_fraction'),'run_status':x.get('run_status')})
            if x.get('run_status')=='complete' and n==TOTAL_GATES: assess['terminal_campaign_status']='PROVISIONAL_CANDIDATE_ONLY'
    (CAMPAIGN/'FINAL_ASSESSMENT.json').write_text(json.dumps(assess,indent=2)+'\n')
    (CAMPAIGN/'FINAL_REPORT.md').write_text('# P6 overnight campaign\n\nSee `FINAL_ASSESSMENT.json`; no candidate is accepted without independent validation.\n')
    write_state(current_stage='complete', candidate_assessment=assess['terminal_campaign_status'], completed_all_gates=assess['best_completed_gate_count']==TOTAL_GATES)
if __name__ == '__main__': main()
