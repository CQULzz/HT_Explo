from pathlib import Path
import json
r=Path('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01');b=json.loads((r/'BACKTRACKING.json').read_text());print('REPEAT_REVISIT',json.dumps({k:b['repeat'][k] for k in ['overall','before_finish','after_finish','proximity_sensitivity']},indent=2))
