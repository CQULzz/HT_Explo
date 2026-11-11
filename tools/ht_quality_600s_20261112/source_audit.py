"""Read-only source-layer and end-of-run evidence; no ROS publication."""
from pathlib import Path
import json, csv, collections
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from std_msgs.msg import String
ROOT=Path('/home/lzz/ht_quality_600s_20261112');RUN=ROOT/'runs/cmu_quality_600s_02'
start=json.loads((RUN/'observations/START.json').read_text())['clock'];rows=list(csv.DictReader((RUN/'observations/metrics.csv').open()));end=float(rows[-1]['time'])
r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(RUN/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
r.set_filter(rosbag2_py.StorageFilter(topics=['/elevation_mapping/elevation_map_raw','/ht_minimal/command_audit','/ht_traversability/global_local']))
counts=collections.Counter();rejections=collections.Counter();last_audit=None;last_source=None;last_map=None;last_nonzero=None;max_bad_pair=0;distributions=[]
while r.has_next():
 topic,data,received=r.read_next()
 if topic=='/ht_minimal/command_audit':
  d=json.loads(deserialize_message(data,String).data)
  if not start<=d['time']<=end:continue
  counts['audits']+=1;last_audit=d
  if not d['allowed']:rejections[d['reason']]+=1
  if d['allowed'] and abs(d['linear_candidate'])+abs(d['angular_candidate'])>1e-8:last_nonzero=d
  continue
 m=deserialize_message(data,GridMap);stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
 if not start<=stamp<=end:continue
 if topic=='/ht_traversability/global_local':last_map=m;continue
 counts['source_maps']+=1;last_source=m
 missing=set(['elevation','variance','observation_age','observation_variance'])-set(m.layers)
 if missing:counts['missing_required_layers']+=1;continue
 arr={name:np.asarray(a.data,np.float32) for name,a in zip(m.layers,m.data)}
 h,v,age,q=[arr[k] for k in ['elevation','variance','observation_age','observation_variance']]
 valid=np.isfinite(h);paired=valid&np.isfinite(age)&np.isfinite(q)&(q>=0)
 bad=int(np.count_nonzero(valid&~paired));max_bad_pair=max(max_bad_pair,bad)
 distinct=paired&(v>.25)&(q<=.25)
 counts['map_cell_observations_total_variance_gt_025_paired_quality_le_025']+=int(np.count_nonzero(distinct))
 if counts['source_maps']%40==0:distributions.append({'elapsed_s':stamp-start,'finite_height_cells':int(valid.sum()),'finite_height_without_pair':bad,'different_quality_cells':int(distinct.sum()),'median_observation_variance':float(np.median(q[paired])) if paired.any() else None})
def decode(m):
 nx=round(m.info.length_x/m.info.resolution);ny=round(m.info.length_y/m.info.resolution)
 return {name:np.roll(np.asarray(a.data,np.float32).reshape((nx,ny),order='F'),(-m.outer_start_index,-m.inner_start_index),(0,1)) for name,a in zip(m.layers,m.data)}
snapshot={}
if last_map is not None:
 arr=decode(last_map);d=last_audit;nx,ny=arr['ht_valid'].shape;res=last_map.info.resolution
 i=int(np.floor(nx/2-(d['x']-last_map.info.pose.position.x)/res));j=int(np.floor(ny/2-(d['y']-last_map.info.pose.position.y)/res))
 if 0<=i<nx and 0<=j<ny:snapshot={'ht_stamp':last_map.header.stamp.sec+last_map.header.stamp.nanosec*1e-9,'eight_scores_at_last_pose':[float(arr['ht_dir_'+str(k)][i,j]) for k in range(8)],'context_valid':float(arr['ht_valid'][i,j]),'raw_ht_obstacle':float(arr['ht_obstacle'][i,j])}
for name,m in [('last_source',last_source),('last_ht',last_map)]:
 if m is not None:
  from rclpy.serialization import serialize_message
  (ROOT/'analysis'/f'{name}.cdr').write_bytes(serialize_message(m))
out={'counts':counts,'maximum_finite_height_cells_without_paired_quality_or_age':max_bad_pair,'rejected_command_reasons':rejections,'last_audit':last_audit,'last_allowed_nonzero_audit':last_nonzero,'last_allowed_nonzero_elapsed_s':None if last_nonzero is None else last_nonzero['time']-start,'end_snapshot':snapshot,'sampled_source_quality':distributions,'passed_wire_contract':bool(counts['source_maps']) and not counts['missing_required_layers'] and max_bad_pair==0,'scope':'Read-only inspection of all recorded source maps with source stamp inside the measurement window. Counts are map-cell observations across frames, not unique terrain cells. Total variance remains available; HT intentionally uses observation_variance with the accepted height/time. End snapshot uses the last recorded HT map, not necessarily the exact final command map; exact command validation is separate.'}
(ROOT/'analysis/SOURCE_AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
