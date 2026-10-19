"""Find actual cycles whose output was a recovery reached after a primary failure."""
from pathlib import Path
import argparse,json,re,collections
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();origin=json.load(open(a.trial/'current/measurement_started.json'))['wall_time'];pending=[];wins=[];recovery=collections.Counter()
for l in (a.trial/'current/tare.log').read_text(errors='replace').splitlines():
 m=re.search(r'\[INFO\] \[([0-9.]+)\]',l)
 if not m:continue
 t=float(m[1])-origin
 if not 0<=t<=600:continue
 if 'HT_SEARCH_AUDIT ' in l:
  d=dict(re.findall(r'(\w+)=([^ ]+)',l.split('HT_SEARCH_AUDIT ',1)[1]));d['t_s']=t;pending.append(d)
  if d['recovery']=='1':recovery[(d['backtrack'],d['termination'])]+=1
 if 'HT_SEARCH_SUMMARY ' in l:
  summary=dict(re.findall(r'(\w+)=([^ ]+)',l.split('HT_SEARCH_SUMMARY ',1)[1]));winner=next((i for i,r in enumerate(pending) if r['target']==summary['output_target'] and r['recovery']=='1' and r['termination']=='REACHED'),None)
  if winner is not None:
   prior=[r for r in pending[:winner] if r['recovery']=='0' and r['termination']!='REACHED']
   if prior:wins.append(dict(t_s=t,output=summary['output_target'],winner=pending[winner],prior_failed_primary=prior,summary=summary))
  pending=[]
result=dict(actual_cycles_recovery_selected_after_failed_primary=len(wins),events=wins,recovery_query_outcomes={('ordinary' if k[0]=='0' else 'backtrack')+'_'+k[1]:v for k,v in recovery.items()},limitations='Uses actual search and summary logs inside the measured600s. A recovery route chosen after a primary failure demonstrates that branch occurred, not counterfactual whole-run superiority, physical ground truth or subsequent route completion.')
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='events'},indent=2))
