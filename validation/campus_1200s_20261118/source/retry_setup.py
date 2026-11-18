from pathlib import Path
import json
root=Path('/home/lzz/ht_campus_1200s_20261118');p=root/'simulation.launch.py';text=p.read_text();assert 'period=90.' in text and 'delay=60.' in text
text=text.replace('period=90.','period=150.').replace('delay=60.','delay=120.');p.write_text(text)
p=root/'run_1200s.sh';p.write_text(p.read_text().replace('explicit_labels_campus_1200s_01','explicit_labels_campus_1200s_02').replace('setup/run.log','setup/run_retry.log'))
plan=json.loads((root/'PLAN.json').read_text());plan['infrastructure_retry']={'failed_attempt':'explicit_labels_campus_1200s_01','failure':'Spawn service queued lidar but timed out before entity appeared; observer never became ready','change':'Only startup timers: spawn delays60/62/64 ->120/122/124 wall seconds, carrier90 ->150 seconds','navigation_changed':False};(root/'PLAN.json').write_text(json.dumps(plan,indent=2))
monitor=Path('/mnt/d/HT-Campus-1200s-20261118/monitor.py');monitor.write_text(monitor.read_text().replace('explicit_labels_campus_1200s_01','explicit_labels_campus_1200s_02'))
print('Prepared startup-only retry; first failed run preserved')
