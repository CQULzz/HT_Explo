import argparse,re,json,csv,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
origin=json.loads((a.trial/'current/measurement_started.json').read_text())['wall_time'];rows=[];completion=[]
for line in (a.trial/'current/tare.log').read_text(errors='replace').splitlines():
 stamp=re.search(r'\[INFO\] \[([0-9.]+)\]',line)
 if not stamp:continue
 t=float(stamp[1])-origin
 if not -5<=t<=600:continue
 if 'COMPLETION_AUDIT ' in line:
  d=dict(re.findall(r'(\w+)=([^ ]+)',line.split('COMPLETION_AUDIT ',1)[1]));d={k:float(v) for k,v in d.items()};d['t_s']=t;completion.append(d)
 if 'HT_CELL_AUDIT ' not in line:continue
 d=dict(re.findall(r'(\w+)=([^ ]+)',line.split('HT_CELL_AUDIT ',1)[1]));d['t_s']=t
 for k,v in list(d.items()):
  try:d[k]=float(v)
  except (ValueError,TypeError):pass
 rows.append(d)
changes=[r for r in rows if r['old']!=r['new']];covered=[r for r in changes if r['new']==2]
trigger=next((r['t_s'] for r in completion if r['global_return'] and r['local_complete']),None)
last={}
for r in rows:last[int(r['cell'])]=r
result=dict(source=str(a.trial.resolve()),rows=len(rows),transitions=len(changes),to_covered=len(covered),covered_reasons=dict(collections.Counter(r['reason'] for r in covered)),first_internal_completion_log_s=trigger,last_transition_window=[r for r in changes if trigger is not None and trigger-10<=r['t_s']<=trigger+.001],tracked_final_state_counts=dict(collections.Counter(int(r['new']) for r in last.values())),last_known_unseen_with_gain=[r for r in last.values() if r['new']==0 and (r['above_small']>0 or r['above_frontier']>0)],unseen_with_gain_unique_cells=len({int(r['cell']) for r in rows if r['old']==0 and r['new']==0 and (r['above_small']>0 or r['above_frontier']>0)}),limitations='Logs UpdateCellStatus decisions only. Does not include external SetCellStatus calls, exact sensor coverage truth, or distinguish geometric vs line-of-sight/corner-connectivity causes of absent candidates. -5s setup window included to retain first measured cycle transitions. Final tracked cells are not the whole global grid.')
(a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
for name,data in [('cells.csv',rows),('transitions.csv',changes),('completion.csv',completion)]:
 with(a.output/name).open('w') as f:
  if data:w=csv.DictWriter(f,fieldnames=data[0].keys());w.writeheader();w.writerows(data)
if rows:
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(1,3,figsize=(17,5))
 for state,color,label in [(0,'gray','UNSEEN'),(1,'orange','EXPLORING'),(2,'green','COVERED')]:
  selected=[r for r in last.values() if int(r['new'])==state];xy=[tuple(map(float,r['xy'].strip('()').split(','))) for r in selected]
  if xy:ax[0].scatter([v[0] for v in xy],[v[1] for v in xy],s=160,marker='s',c=color,alpha=.6,label=label)
 ax[0].set_aspect('equal');ax[0].set_xlabel('Cell center X (m)');ax[0].set_ylabel('Cell center Y (m)');ax[0].set_title('Tracked cells only, final known state');ax[0].legend()
 c=collections.Counter(r['reason'] for r in covered);ax[1].barh(list(c),list(c.values()));ax[1].set_xlabel('Transitions to COVERED');ax[1].tick_params(axis='y',labelsize=7)
 for k in ['global_exploring','eligible','unreachable']:ax[2].plot([r['t_s'] for r in completion],[r[k] for r in completion],label=k)
 if trigger is not None:ax[2].axvline(trigger,color='red',ls='--',label='Internal finish trigger')
 ax[2].set_xlabel('Measurement seconds');ax[2].set_title('Logged global tour counts');ax[2].legend()
 fig.tight_layout();fig.savefig(a.output/'cell_coverage.png',dpi=180)
print(json.dumps(result,indent=2))
