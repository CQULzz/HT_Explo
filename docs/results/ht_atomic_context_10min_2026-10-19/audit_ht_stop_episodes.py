from pathlib import Path
import argparse,json,csv,re,collections
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=list(csv.DictReader((a.trial/'current/timeseries.csv').open()));origin=json.load(open(a.trial/'current/measurement_started.json'))['wall_time'];runs=[];start=None
for r in rows:
 stopped=abs(float(r['cmd_speed_mps']))<1e-8 and abs(float(r['cmd_yaw_rate_rps']))<1e-8
 if stopped and start is None:start=r
 if not stopped and start is not None:runs.append(dict(sampled_start_s=float(start['t_s']),sampled_end_s=float(r['t_s']),sampled_duration_s=float(r['t_s'])-float(start['t_s']),pose=[float(start[k]) for k in ['x_m','y_m','yaw_rad']]));start=None
if start:runs.append(dict(sampled_start_s=float(start['t_s']),sampled_end_s=float(rows[-1]['t_s']),sampled_duration_s=float(rows[-1]['t_s'])-float(start['t_s']),pose=[float(start[k]) for k in ['x_m','y_m','yaw_rad']],right_censored=True))
runs.sort(key=lambda r:r['sampled_duration_s'],reverse=True);runs=runs[:5]
for r in runs:r['queries']=[]
for l in (a.trial/'current/tare.log').read_text(errors='replace').splitlines():
 m=re.search(r'\[INFO\] \[([0-9.]+)\]',l)
 if not m or 'HT_SEARCH_AUDIT ' not in l:continue
 t=float(m[1])-origin
 for r in runs:
  if r['sampled_start_s']<=t<=r['sampled_end_s']:
   d=dict(re.findall(r'(\w+)=([^ ]+)',l.split('HT_SEARCH_AUDIT ',1)[1]));d['t_s']=t;r['queries'].append(d)
for r in runs:r['termination_counts']=dict(collections.Counter(q['termination'] for q in r['queries']))
a.output.write_text(json.dumps(dict(episodes=runs,limitations='Zero commands at0.5s CSV samples, approximate boundaries. Full20Hz command audit supplies longest_zero_command_s. Search timestamps are post-search logs; timeouts do not prove physical impossibility.'),indent=2)+'\n')
