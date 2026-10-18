"""Read recorded search/summary pairs to detect queued recovery starvation."""
import argparse,re,json,csv,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
origin=json.load(open(a.trial/'current/measurement_started.json'))['wall_time'];queries=[];cycles=[]
for line in (a.trial/'current/tare.log').read_text(errors='replace').splitlines():
 m=re.search(r'\[INFO\] \[([\d.]+)\]',line)
 if not m:continue
 t=float(m[1])-origin
 if not 0<=t<=600:continue
 def decode(marker):
  d=dict(re.findall(r'(\w+)=([^ ]+)',line.split(marker,1)[1]));d['t_s']=t
  for k,v in list(d.items()):
   try:d[k]=float(v)
   except (ValueError,TypeError):pass
  return d
 if 'HT_SEARCH_AUDIT ' in line:queries.append(decode('HT_SEARCH_AUDIT '))
 if 'HT_SEARCH_SUMMARY ' in line:
  d=decode('HT_SEARCH_SUMMARY ');d['recorded_queries']=len(queries);d['recovery_attempts']=sum(r['recovery']!=0 for r in queries);d['backtrack_attempts']=sum(r['backtrack']!=0 for r in queries);d['all_queries_timed_out']=bool(queries) and all(r['termination']=='TIME_LIMIT' for r in queries);d['queued_extra_targets']=max(0,d['targets']-d['primary']);d['goals']=';'.join(str(r['goal']) for r in queries);cycles.append(d);queries=[]
starved=[r for r in cycles if r['output_target']<0 and r['queued_extra_targets']>0 and r['recovery_attempts']==0 and r['all_queries_timed_out']]
s=dict(cycles=len(cycles),failed_all_timeout_with_unattempted_extra_targets=len(starved),first_starved_s=starved[0]['t_s'] if starved else None,last_starved_s=starved[-1]['t_s'] if starved else None,post60_cycles=sum(r['t_s']>60 for r in cycles),post60_starved_cycles=sum(r['t_s']>60 for r in starved),post60_recovery_attempts=sum(r['recovery_attempts'] for r in cycles if r['t_s']>60),most_common_starved_goals=collections.Counter(r['goals'] for r in starved).most_common(8),limitations='Targets minus primary combines recovery and optional backtrack. Search logs show queued alternatives were not attempted, not that they are feasible. This audit cannot attribute the different initial trajectory to a single variable or prove physical coverage.')
(a.output/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
with (a.output/'cycles.csv').open('w') as f:
 if cycles:w=csv.DictWriter(f,fieldnames=cycles[0]);w.writeheader();w.writerows(cycles)
print(json.dumps(s,indent=2))
