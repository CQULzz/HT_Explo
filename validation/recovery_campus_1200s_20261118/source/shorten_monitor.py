from pathlib import Path
p=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118/monitor_live.py');s=p.read_text(encoding='utf-8-sig').replace("if p.exists():print('ACTUAL_NAVIGATION_VERIFIED',json.loads(p.read_text()))","if p.exists():print('ACTUAL_NAVIGATION_VERIFIED',len(json.loads(p.read_text())))");p.write_text(s)
