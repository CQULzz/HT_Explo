from pathlib import Path
import json,hashlib,csv,bisect
import numpy as np
R=Path('/home/w_lzz/ht-iterations-20261105');O=R/'cycle3_offline';O.mkdir(exist_ok=True)
labels=['baseline_seed42_b01','baseline_seed99_b02','threshold_seed42_c01','threshold_seed99_c02','queue_seed42_c03','queue_seed99_c04','retained_repeat42_r01']
report={'scope':'Read-only existing cycle2 evidence. No new simulation, ROS playback or vehicle commands. 1Hz producer metrics; callback residuals computed per sample, never by subtracting percentiles. Timer service includes lock wait, so it is not exclusive GPU compute time.','runs':{}}
def quant(v):return {'n':len(v),**dict(zip(['p50','p95','max'],map(float,np.percentile(v,[50,95,100]))))} if v else {'n':0}
for label in labels:
 p=R/'cycle2'/label;groups={};first={}
 for line in (p/'events.jsonl').open():
  item=json.loads(line)
  if item['topic'] not in ['ht_performance','input_performance']:continue
  q=json.loads(item['data']);first.setdefault(item['topic'],q)
  if item['topic']!='ht_performance':continue
  values={'source_age_callback_s':q['source_age_at_callback_s'],'source_age_publish_s':q['source_age_at_publish_s'],'ros_elapsed_callback_to_publish_s':q['source_age_at_publish_s']-q['source_age_at_callback_s'],'callback_service_wall_s':q['callback_service_s'],'queue_wait_wall_s':q.get('queue_wait_s')}
  values.update({'stage_'+k:v for k,v in q.get('stages',{}).items()})
  for k,v in values.items():
   if isinstance(v,(int,float)):groups.setdefault(k,[]).append(v)
 stats=json.loads((p/'mapper_stats.json').read_text())
 report['runs'][label]={'metrics':{k:quant(v) for k,v in groups.items()},'mapper_stats':stats,'sample_performance_fields':first,'sha256':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['events.jsonl','mapper_stats.json','manifest.json']}}
 for name in ['source_age_callback_s','source_age_publish_s','ros_elapsed_callback_to_publish_s','callback_service_wall_s','queue_wait_wall_s']:
  print(label,name,report['runs'][label]['metrics'].get(name))
(O/'PIPELINE_DIAGNOSIS.json').write_text(json.dumps(report,indent=2))
