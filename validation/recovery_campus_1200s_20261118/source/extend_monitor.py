from pathlib import Path
p=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118/monitor_live.py');s=p.read_text();s += "\np=r/'simulation.log'\nif p.exists():\n lines=[x for x in p.read_text(errors='replace').splitlines() if 'EXPLORATION_DIAG' in x];print('PLANNER',lines[-1:] if lines else 'not yet')\n";p.write_text(s)
