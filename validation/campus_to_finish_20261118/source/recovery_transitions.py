from pathlib import Path
import json
r=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01');start=json.loads((r/'observations/START.json').read_text())['clock'];last=None
for line in (r/'observations/events.jsonl').open():
 e=json.loads(line)
 if e['kind']!='/ht_minimal/recovery' or e['time']<start:continue
 d=e['data'];key=(d['state'],d['plans'],d['completed'],d['invalidated'])
 if key!=last:print(json.dumps({'elapsed_s':e['time']-start,**{k:d.get(k) for k in ['state','plans','completed','invalidated','exploration_finished','x','y','goal_x','goal_y','search_outcome','search_progress_m']}}));last=key
