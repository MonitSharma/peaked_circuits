"""Read original Nexus result chunks; preserve originals and audit SDK assembly."""
import json, re, hashlib, inspect
from pathlib import Path
from collections import Counter
import qnexus as qnx
from qnexus.client import get_nexus_client
from qnexus.client.jobs._execute import fetch_qsys_result_by_id
from qnexus.models.references import ResultVersions
from analyze_p6_four_batches import decode
ROOT = Path(__file__).resolve().parents[1]
RAW = [
    ROOT / 'results/hardware/p6_helios_100shot_20260907/raw_result.json',
    ROOT / 'results/hardware/p6_helios_100shot_20260907_batch2/raw_result.json',
    ROOT / 'results/hardware/p6_helios_100shot_20260907_batch3/raw_result.json',
    ROOT / 'results/hardware/p6_helios_100shot_20260907_batch4/raw_result.json',
    ROOT / 'results/hardware/p6_helios_100shot_20260907_batch5/raw_result.json',
]

OUT = ROOT / 'results/hardware/p6_chunk_audit_20260907'
RECORDS = [ROOT/'hardware_campaign/p6_batch_001/job_records/discovery.json'] + [ROOT/f'hardware_campaign/p6_batch_00{i}/job_record.json' for i in range(2,6)]
def digest(b): return hashlib.sha256(b).hexdigest()
def frames(t):
    matches=list(re.finditer(r'OUTPUT\tRESULT\t([01])\t(m\d{3})\[0\]',t))
    assert len(matches)%62 == 0
    out=[]
    for k in range(0,len(matches),62):
        f={m[2]:m[1] for m in matches[k:k+62]}
        assert set(f)=={f'm{i:03d}' for i in range(62)}
        out.append(''.join(f[f'm{i:03d}'] for i in range(62)))
    return out
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'sdk_assembly_source.txt').write_text(inspect.getsource(fetch_qsys_result_by_id))
    audit=[]; pooled=[]
    for i,(record,path) in enumerate(zip(RECORDS,RAW),1):
        rec=json.loads(record.read_text()); dest=OUT/f'batch{i}';dest.mkdir(exist_ok=True)
        chunks=[]; shots=[]
        for n in range(100):
            r=get_nexus_client().get(f'/api/qsys_results/v1beta2/partial/{rec["result_id"]}',params={'version':ResultVersions.DEFAULT.value,'chunk_number':n,'scope':'user'})
            if r.status_code==404: break
            r.raise_for_status(); body=r.json()
            (dest/f'chunk_{n:03d}.json').write_text(json.dumps(body,indent=2))
            t=body['data']['attributes']['results'];assert isinstance(t,str)
            chunks.append(t);shots.extend(frames(t))
        else: raise RuntimeError('Chunk bound exceeded')
        assert len(shots)==100
        joined=chunks[0]
        for t in chunks[1:]:
            joined += joined.split('END')[0]+'\n'.join(line for line in t.splitlines() if 'OUTPUT' in line)+'END\t0\n'
        bitcode=qnx.qir.get(id=rec['qir_artifact_id']).download_qir()
        (dest/'provider_input.bc').write_bytes(bitcode)
        (dest/'shots.json').write_text(json.dumps(shots,indent=2))
        row={'batch':i,'job_id':rec['job_id'],'result_id':rec['result_id'],'chunk_frames':[len(frames(t)) for t in chunks],'original_sha256':digest(path.read_bytes()),'replayed_sdk_matches_saved':joined==path.read_text(),'downloaded_bitcode_matches_local':bitcode==(ROOT/'results/hardware/p6_helios_50shot_20260829/submitted.qir.bc').read_bytes(),'unique':len(set(shots)),'analysis':decode(shots)}
        audit.append(row);pooled.extend(shots)
        print({k:v for k,v in row.items() if k!='analysis'},flush=True)
    result={'batches':audit,'pooled':decode(pooled),'frequency_histogram':dict(Counter(Counter(pooled).values())),'source':'Original API chunks, parsed separately; no deduplication or truncation'}
    (OUT/'audit.json').write_text(json.dumps(result,indent=2))
    (OUT/'shots_400.json').write_text(json.dumps(pooled,indent=2))
    print('pooled',len(pooled),len(set(pooled)))
if __name__=='__main__': main()
