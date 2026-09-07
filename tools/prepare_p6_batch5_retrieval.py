#!/usr/bin/env python3
"""Record the completed P6 Batch 005 result reference for chunk-level retrieval."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import qnexus as qnx

ROOT=Path(__file__).resolve().parents[1]
JOB_ID='35bab525-cea9-48ac-bdd0-9a3e067a2dea'
RECORD=ROOT/'hardware_campaign/p6_batch_005/job_record.json'

def main():
    job=qnx.jobs.get(id=JOB_ID); status=qnx.jobs.status(job)
    if str(getattr(status.status,'value',status.status))!='COMPLETED': raise SystemExit(f'Job is not completed: {status}')
    refs=list(qnx.jobs.results(job))
    if len(refs)!=1: raise SystemExit(f'Expected one result reference, got {len(refs)}')
    ref=refs[0]; record=json.loads(RECORD.read_text())
    record.update({'status':'RETRIEVED','result_id':str(getattr(ref,'id',ref)),'returned_shots':100,'reported_hqc':float(status.cost),'queued_at_utc':status.queued_time.isoformat() if status.queued_time else None,'running_at_utc':status.running_time.isoformat() if status.running_time else None,'completed_at_utc':status.completed_time.isoformat() if status.completed_time else None,'retrieval_method':'original_qsys_chunks'})
    RECORD.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'job_id':JOB_ID,'result_id':record['result_id'],'reported_hqc':record['reported_hqc']},indent=2))
if __name__=='__main__': main()
