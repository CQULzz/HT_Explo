#!/usr/bin/env python3
"""Join HT diagnostic source stamps to observed CuPy scan callbacks, read-only."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();trial=args.trial.resolve()
    if args.output.exists():raise FileExistsError(args.output)
    started=trial/'current/measurement_started.json'
    origin=json.loads(started.read_text())['wall_time']
    duration=json.loads((trial/'summary.json').read_text())['duration_s']
    context=trial/'current/ht_diagnostics.json'
    trace=trial/'current/cupy_timing.jsonl'
    callbacks={}
    for line in trace.read_text().splitlines():
        row=json.loads(line)
        if row['kind']=='callback' and row['operation']=='scan':
            callbacks.setdefault(round(row['source_stamp']*1e6),[]).append(row)
    rows=[];unmatched=[];ambiguous=[]
    for ht in json.loads(context.read_text()):
        source=ht['stamp_s']
        if not 0<=source-origin<duration:continue
        matches=callbacks.get(round(source*1e6),[])
        matches=[r for r in matches if abs(r['source_stamp']-source)<1e-6]
        if not matches:
            unmatched.append(source);continue
        if len(matches)!=1:
            ambiguous.append(source);continue
        callback=matches[0]
        end=callback['wall_time'];start=end-callback['elapsed_s']
        ht_start=source+ht['source_age_at_callback_s']
        rows.append(dict(source_s=source-origin,source_stamp=source,
            source_stamp_delta_s=callback['source_stamp']-source,
            source_age_at_scan_callback_start_s=start-source,
            scan_callback_elapsed_s=callback['elapsed_s'],
            scan_callback_thread_cpu_s=callback['cpu_s'],
            scan_end_to_ht_callback_start_s=ht_start-end,
            source_age_at_ht_callback_start_s=ht['source_age_at_callback_s'],
            ht_callback_elapsed_s=ht['elapsed_s']))
    rows.sort(key=lambda r:r['source_age_at_ht_callback_start_s'],reverse=True)
    result=dict(source=str(trial),tested_commit=json.loads((trial/'manifest.json').read_text())['git_head'],
        matched=len(rows),unmatched=unmatched,ambiguous=ambiguous,
        input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [started,context,trace]},
        oldest_on_ht_arrival=rows[:10],
        limitations='Identical source stamp joins, not nearest wall time. Callback start uses end wall clock minus monotonic elapsed and assumes no wall-clock jumps. Scan start age includes producer/transport/executor waiting; scan duration includes decode/TF/lock/device waits; scan-end to HT-start includes publication/transport/HT queue. These measurements do not separate those subcauses or establish GPU kernel execution time. Rows are individual matched frames; percentile sums are not used.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'},indent=2))


if __name__=='__main__':main()
