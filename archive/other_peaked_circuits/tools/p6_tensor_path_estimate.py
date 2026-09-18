#!/usr/bin/env python3
"""Estimate a full amplitude tensor-network contraction path on CPU."""
from __future__ import annotations
import json,re,time
from pathlib import Path
import numpy as np
import opt_einsum as oe

ROOT=Path(__file__).resolve().parents[1]
QASM=ROOT/'results/hardware/p6_helios_50shot_20260829/source.qasm'
OUT=ROOT/'results/hardware/p6_gpu_feasibility_20260907'

def build_network():
    current=list(range(62)); next_label=62; operands=[]; gate_counts={'u3':0,'cz':0}
    for q in range(62): operands.extend(([2],tuple([current[q]])))
    for line in QASM.read_text().splitlines():
        m=re.match(r'\s*u3\([^)]*\)\s+q\[(\d+)\];',line)
        if m:
            q=int(m.group(1)); inp=current[q]; out=next_label; next_label+=1
            operands.extend(([2,2],tuple([inp,out])));current[q]=out;gate_counts['u3']+=1
            continue
        m=re.match(r'\s*cz\s+q\[(\d+)\],q\[(\d+)\];',line)
        if m:
            a,b=map(int,m.groups()); ia,ib=current[a],current[b]; oa,ob=next_label,next_label+1;next_label+=2
            operands.extend(([2,2,2,2],tuple([ia,ib,oa,ob])));current[a],current[b]=oa,ob;gate_counts['cz']+=1
    for q in range(62): operands.extend(([2],tuple([current[q]])))
    return operands,gate_counts,next_label

def main():
    operands,gates,nlabels=build_network(); started=time.perf_counter()
    arrays=[]
    for i in range(0,len(operands),2):
        arrays.extend((np.empty(operands[i],dtype=np.float64),operands[i+1]))
    path,info=oe.contract_path(*arrays,optimize='greedy')
    elapsed=time.perf_counter()-started
    largest=int(info.largest_intermediate); opt_flops=float(info.opt_cost); largest_bytes=largest*16
    payload={'schema_version':'p6-tensor-path-estimate-v1','provider_calls':0,'gpu_calls':0,'path_optimizer':'opt_einsum.greedy','source_qasm':str(QASM),'gate_counts':gates,'tensor_count':len(operands),'index_count':nlabels,'path_search_seconds':elapsed,'naive_flops':str(info.naive_cost),'optimized_flops':str(info.opt_cost),'largest_intermediate_elements':largest,'largest_intermediate_log2_elements':largest.bit_length()-1,'largest_intermediate_complex128_bytes':largest_bytes,'largest_intermediate_gib':largest_bytes/2**30,'largest_intermediate_eib':largest_bytes/2**60,'path_length':len(path),'decision':'GPU_PATH_ESTIMATE_REQUIRED','caveat':'Greedy path is a heuristic upper bound; it is not a proof of the optimal contraction cost.'}
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'tensor_path_estimate.json').write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps(payload,indent=2))
if __name__=='__main__':main()
