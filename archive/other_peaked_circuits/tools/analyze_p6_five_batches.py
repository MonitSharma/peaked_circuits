#!/usr/bin/env python3
"""Analyze corrected P6 batches 1-5 and pool 500 shots."""
from __future__ import annotations
import hashlib,json,re
from collections import Counter
from pathlib import Path
from p12_recovery.recovery import bitwise_majority_string,cluster_consensus,method_agreement,most_frequent_string,weighted_observed_medoid
ROOT=Path(__file__).resolve().parents[1]
SHOT_FILES=[ROOT/f'results/hardware/p6_chunk_audit_20260907/batch{i}/shots.json' for i in range(1,5)] + [ROOT/'results/hardware/p6_helios_100shot_20260907_batch5/shots.json']
OUT=ROOT/'results/hardware/p6_five_batch_corrected_analysis_20260907'
def decode(shots):
 c=Counter(shots); methods=[most_frequent_string(c),bitwise_majority_string(c),weighted_observed_medoid(c),cluster_consensus(c)]
 return {'shot_count':len(shots),'unique_strings':len(c),'top_counts':[{'bitstring':s,'count':n} for s,n in c.most_common(10)],'candidates':[m.model_dump(mode='json') for m in methods],'method_agreement':method_agreement(methods)}
def ham(a,b): return sum(x!=y for x,y in zip(a,b,strict=True))
def get(d,m): return next(x['canonical_bitstring'] for x in d['candidates'] if x['method_name']==m)
def main():
 batches=[json.loads(p.read_text()) for p in SHOT_FILES]; pooled=sum(batches,[]); ds=[decode(b) for b in batches]; modes=[get(d,'most_frequent') for d in ds]
 p1=[sum(s[i]=='1' for s in pooled)/len(pooled) for i in range(62)]
 payload={'schema_version':'p6-five-corrected-batches-v1','source':'original Nexus chunks parsed independently','provider_submission_performed':False,'batch_files':[str(p) for p in SHOT_FILES],'batches':ds,'pooled_500':decode(pooled),'mode_comparison':{'batch_modes':modes,'pairwise_hamming':[[ham(a,b) for b in modes] for a in modes]},'bit_stability':{'threshold':'p1 <= 0.25 or p1 >= 0.75','stable_position_count':sum(p<=.25 or p>=.75 for p in p1),'bitwise_ensemble_candidate':''.join('1' if p>.5 else '0' for p in p1),'p1_by_position':p1},'interpretation':{'decision':'NO_REPRODUCIBLE_FULL_CANDIDATE','reason':'Corrected chunk-level data have no repeated bitstring across 500 shots; decoder outputs are summaries of a diffuse distribution.'}}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'analysis.json').write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps({'batch_modes':modes,'pooled':payload['interpretation'],'pooled_top':payload['pooled_500']['top_counts'][:5],'bit_stability':payload['bit_stability']['stable_position_count']},indent=2))
if __name__=='__main__': main()
