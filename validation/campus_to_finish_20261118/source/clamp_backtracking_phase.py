from pathlib import Path
import json
work=Path('/mnt/d/HT-Campus-To-Finish-20261118');p=work/'analyze_backtracking.py';s=p.read_text().replace("'end_s':begin+300","'end_s':min(begin+300,float(t[-1]))");p.write_text(s)
r=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01');p=r/'BACKTRACKING.json';a=json.loads(p.read_text());duration=json.loads((r/'RESULT.json').read_text())['summary']['elapsed_s']
for phase in a['repeat']['phases']:phase['end_s']=min(phase['end_s'],duration)
p.write_text(json.dumps(a,indent=2));dest=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/campus_to_finish_20261118');(dest/'BACKTRACKING.json').write_bytes(p.read_bytes())
