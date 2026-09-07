#!/usr/bin/env python3
"""CPU-only P6 contraction feasibility screen; no provider or GPU calls."""
from __future__ import annotations
import json, math, re, statistics
from pathlib import Path
import networkx as nx

ROOT=Path(__file__).resolve().parents[1]
QASM=ROOT/'results/hardware/p6_helios_50shot_20260829/source.qasm'
OUT=ROOT/'results/hardware/p6_gpu_feasibility_20260907'

def main():
    text=QASM.read_text()
    gates=[]; edges=[]
    for line in text.splitlines():
        m=re.match(r'\s*(u3)\([^)]*\)\s+q\[(\d+)\];',line)
        if m:gates.append(('u3',int(m.group(2))))
        m=re.match(r'\s*cz\s+q\[(\d+)\],q\[(\d+)\];',line)
        if m:
            a,b=map(int,m.groups());gates.append(('cz',a,b));edges.append((a,b))
    g=nx.Graph();g.add_nodes_from(range(62));g.add_edges_from(edges)
    tw_fill,decomp_fill=nx.approximation.treewidth_min_fill_in(g)
    tw_degree,decomp_degree=nx.approximation.treewidth_min_degree(g)
    degrees=sorted(dict(g.degree()).values())
    payload={
      'schema_version':'p6-cpu-feasibility-v1','provider_calls':0,'gpu_calls':0,
      'source_qasm':str(QASM),'qubits':62,'u3_count':sum(x[0]=='u3' for x in gates),'cz_count':sum(x[0]=='cz' for x in gates),
      'interaction_edges':g.number_of_edges(),'connected_components':nx.number_connected_components(g),
      'degree_summary':{'min':min(degrees),'median':statistics.median(degrees),'max':max(degrees)},
      'logical_graph_treewidth_heuristics':{'min_fill_in':tw_fill,'min_degree':tw_degree,'interpretation':'heuristic upper bounds for the 62-node interaction graph, not a full gate tensor-network contraction width'},
      'dense_statevector':{'complex128_bytes':2**62*16,'complex128_eib':64.0},
      'available_local_path_tools':{'cotengra':False,'opt_einsum':False,'cuquantum':False,'qiskit_aer':False,'networkx':True},
      'decision':'NO_GPU_RENTAL_YET','reason':'The logical graph screen is complete, but a tensor-level contraction path search requires installing a path optimizer or running on a GPU-capable environment. CPU MPS/MPO fidelity studies already failed to produce a stable candidate.'
    }
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'feasibility.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))
if __name__=='__main__':main()
