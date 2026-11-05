from pathlib import Path
from collections import Counter
import json
R=Path('/home/w_lzz/ht-iterations-20261105/profile_repeat120_r05');report={}
for label in ['ht','mapper']:
 leaves=Counter();modules=Counter();threads=Counter();total=0;executor=0
 for line in (R/f'profile_{label}_gil.raw').read_text().splitlines():
  stack,count=line.rsplit(' ',1);count=int(count);total+=count;frames=stack.split(';');leaves[frames[-1]]+=count
  if 'executors.py' in frames[-1]:executor+=count
  threads[frames[0]]+=count
 report[label]={'gil_sample_count':total,'leaf_in_rclpy_executor_samples':executor,'leaf_executor_fraction':executor/total,'top_leaf':leaves.most_common(15),'threads':threads.most_common()}
(R/'GIL_PROFILE_SUMMARY.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
