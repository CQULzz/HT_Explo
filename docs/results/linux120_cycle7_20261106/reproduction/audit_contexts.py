from pathlib import Path
import sys,json,hashlib,argparse
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('--decoder-deps',type=Path);args=parser.parse_args()
if args.decoder_deps:sys.path.insert(0,str(args.decoder_deps))
from scipy.ndimage import distance_transform_edt,uniform_filter,maximum_filter
from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
r=args.run;wanted={};events=[];outside=[]
window_end=json.loads((r/'READY.json').read_text())['first_sensor_cycle_sim']+json.loads((r/'DONE.json').read_text())['elapsed_sim']
for p in sorted((r/'contexts').glob('*.npz')):
 with np.load(p) as d:
  if float(d['source_stamp'])>window_end:outside.append(p.name);continue
  known=d['observed']|np.isfinite(d['obstacle_context']);uncertain=d['rejected']&~np.isfinite(d['obstacle_context'])
  near=distance_transform_edt(~known)*float(d['geometry'][2])<=.25
  physical=(near&~uncertain&~d['physical_exclusion'])[25:-25,25:-25]
  support=(uniform_filter(near.astype(np.float32),size=51,mode='constant')[25:-25,25:-25]>=.9)&~maximum_filter(uncertain,size=51,mode='constant')[25:-25,25:-25]&~d['physical_exclusion'][25:-25,25:-25]
  occ=np.isfinite(d['obstacle_context'])[25:-25,25:-25];support|=occ
  checks={'physical_support_exact':bool(np.array_equal(physical,d['physical_support'])),'context_support_exact':bool(np.array_equal(support,d['support'])),'occupied_exact':bool(np.array_equal(occ,d['occupied'])),'occupied_probability_zero':bool(np.all(d['probabilities'][:,occ]==0)),'height_finite':bool(np.isfinite(d['height']).all())}
  layers={'ht_valid':d['support'].astype(np.float32),'ht_observation_valid':d['physical_support'].astype(np.float32),'ht_obstacle':d['occupied'].astype(np.float32)}
  layers.update({f'ht_dir_{i}':np.where(d['support'],d['probabilities'][i],np.nan) for i in range(8)})
  e={'file':p.name,'source_stamp':float(d['source_stamp']),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checks':checks,'paired_published_map':False}
  key=tuple(map(int,p.stem.split('_')));wanted[key]=(layers,e);events.append(e)
for p in (r/'bag').glob('*.mcap'):
 with p.open('rb') as f:
  for _,channel,message in make_reader(f,validate_crcs=True).iter_messages(topics=['/ht_real/traversability']):
   m=deserialize_message(message.data,GridMap);key=(m.header.stamp.sec,m.header.stamp.nanosec)
   if key not in wanted:continue
   layers,e=wanted[key];e['paired_published_map']=True
   e['checks']['map_zero_start']=m.outer_start_index==m.inner_start_index==0
   for k,v in layers.items():
    got=np.array(m.data[m.layers.index(k)].data).reshape(v.shape,order='F')
    e['checks']['published_'+k+'_exact']=bool(np.array_equal(got,v,equal_nan=True))
res={'run':r.name,'post_measurement_contexts_preserved':outside,'sampled_contexts':len(events),'paired_published_maps':sum(e['paired_published_map'] for e in events),'all_passed':bool(events) and all(e['paired_published_map'] and all(e['checks'].values()) for e in events),'events':events,'scope':'Sparse10-source-second inputs/masks and all11 corresponding published score/mask layers. No physical-truth or full-time coverage claim.'}
(r/'CONTEXT_VERIFICATION.json').write_text(json.dumps(res,indent=2));print({k:v for k,v in res.items() if k!='events'})
