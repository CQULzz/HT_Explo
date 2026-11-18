from pathlib import Path
p=Path('/mnt/d/HT-Campus-To-Finish-20261118/results/logs/simulation.log');lines=p.read_text(errors='replace').splitlines()
for i,line in enumerate(lines):
 if 'Exploration completed' in line:
  print('\n'.join(lines[max(0,i-20):i+5]));break
