#!/usr/bin/env python3
"""Match observer samples to every profiled mapper scan callback by source stamp."""
import argparse,bisect,csv,hashlib,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('trial',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    files=[a.trial/'current/cupy_timing.jsonl',a.trial/'health.csv',a.trial/'current/cupy_processing_stats.json',a.trial/'current/measurement_started.json']
    scans=[json.loads(l) for l in files[0].read_text().splitlines() if '"operation":"scan"' in l]
    scans=[r for r in scans if r['kind']=='callback' and r['operation']=='scan']
    stamps=[r['source_stamp'] for r in scans];monotonic=all(b>a for a,b in zip(stamps,stamps[1:]));stats=json.loads(files[2].read_text());origin=json.loads(files[3].read_text())['wall_time'];duration=json.loads((a.trial/'summary.json').read_text())['duration_s']
    matches=[];missing=[]
    with files[1].open() as stream:
        for row in csv.DictReader(stream):
            if not 0<=float(row['wall_time'])-origin<duration or not row['scan_source_age_s']:continue
            stamp=float(row['wall_time'])-float(row['scan_source_age_s']);j=bisect.bisect_left(stamps,stamp)
            candidates=range(max(0,j-1),min(len(stamps),j+2));found=[i for i in candidates if abs(stamps[i]-stamp)<1e-4]
            if len(found)!=1:missing.append(dict(time_s=float(row['wall_time'])-origin,source_stamp=stamp));continue
            i=found[0];observer=int(row['scan_count']);matches.append(dict(time_s=float(row['wall_time'])-origin,source_stamp=stamps[i],observer_count=observer,mapper_callback_ordinal=i+1,count_offset=observer-i-1))
    offsets=sorted(set(r['count_offset'] for r in matches))
    result=dict(source=str(a.trial.resolve()),trace_callbacks=len(scans),final_received_callbacks=stats['received_cloud_callbacks'],final_processed_clouds=stats['processed_clouds'],
        trace_matches_final_receive_count=len(scans)==stats['received_cloud_callbacks'],source_stamps_strictly_increasing=monotonic,exact_source_stamp_checkpoints=len(matches),missing_observer_samples=missing,
        count_offsets=offsets,constant_relative_offset=bool(matches) and len(offsets)==1,
        supports_no_net_relative_loss_in_matched_window=monotonic and len(scans)==stats['received_cloud_callbacks'] and len(matches)>1 and len(offsets)==1 and not missing,
        checkpoints=matches,input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        limitations='Uses every profiled scan callback ordinal, not a five-second mapper stats snapshot. Observer is sampled at1Hz and source stamps must match within1e-4s. Constant offset supports no net relative observer/mapper loss inside the matched interval; cannot prove source continuity, full sensor truth, or exclude both subscribers losing the same messages. Strictly increasing scan stamps required for binary matching.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['checkpoints','input_sha256']},indent=2))

if __name__=='__main__':main()
