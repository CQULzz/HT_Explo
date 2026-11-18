from pathlib import Path
import json,csv,collections
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Path as PathMsg
from std_msgs.msg import Bool
root=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');windows=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118')
cases={'native':Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02'),'ht':Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')}
def xyz(m):
 f={p.name:p.offset for p in m.fields};dt=np.dtype({'names':['x','y','z'],'formats':['<f4']*3,'offsets':[f[k] for k in ['x','y','z']],'itemsize':m.point_step});a=np.ndarray((m.height,m.width),dtype=dt,buffer=m.data,strides=(m.row_step,m.point_step));return np.column_stack([a[k].ravel() for k in ['x','y','z']])
summary={}
for tag,run in cases.items():
 rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));topics=['/filtered_frontier_cloud','/uncovered_cloud','/global_path','/exploration_finish','/exploring_cell_vis_cloud','/viewpoint_vis_cloud','/uncovered_frontier_cloud'];rd.set_filter(rosbag2_py.StorageFilter(topics=topics));start=json.loads((run/'observations/START.json').read_text())['clock'];finish=None;latest={};before={};rows=[];unions=collections.defaultdict(set);counts=collections.Counter();firstlast={}
 while rd.has_next():
  topic,data,t=rd.read_next();stamp=t/1e9
  if stamp<start:continue
  counts[topic]+=1
  if topic=='/exploration_finish':
   m=deserialize_message(data,Bool)
   if m.data and finish is None:finish=stamp;before=latest.copy()
   continue
  if topic=='/global_path':
   m=deserialize_message(data,PathMsg);pts=np.array([[p.pose.position.x,p.pose.position.y,p.pose.position.z] for p in m.poses],float).reshape(-1,3)
  else:m=deserialize_message(data,PointCloud2);pts=xyz(m);pts=pts[np.isfinite(pts).all(1)]
  latest[topic]={'time':stamp,'elapsed_s':stamp-start,'points':pts}
  rows.append({'elapsed_s':stamp-start,'topic':topic,'points':len(pts)})
  if finish is None and topic in ['/filtered_frontier_cloud','/uncovered_cloud']:
   unions[topic].update(map(tuple,np.unique(np.floor(pts/.5).astype(np.int32),axis=0)))
   cells=np.unique(np.floor(pts[:,:2]/9.6).astype(np.int32),axis=0)
   for cell in cells:
    k=topic+':'+','.join(map(str,cell));firstlast.setdefault(k,[stamp-start,stamp-start,0]);firstlast[k][1]=stamp-start;firstlast[k][2]+=1
 with (root/(tag+'_task_cloud_counts.csv')).open('w') as stream:
  w=csv.DictWriter(stream,fieldnames=['elapsed_s','topic','points']);w.writeheader();w.writerows(rows)
 details={}
 for topic,v in before.items():
  p=v.pop('points');details[topic]={**v,'points':len(p),'bounds_xyz':[p.min(0).tolist(),p.max(0).tolist()] if len(p) else None};np.save(root/(tag+'_pre_finish_'+topic.strip('/')+'.npy'),p)
 arrays={topic.strip('/'):((np.array(list(values),np.float32).reshape(-1,3)+.5)*.5) for topic,values in unions.items()};np.savez_compressed(root/(tag+'_task_cloud_union.npz'),**arrays)
 (root/(tag+'_task_cells_history.json')).write_text(json.dumps(firstlast,indent=2))
 summary[tag]={'first_finish_receipt_elapsed_s':None if finish is None else finish-start,'recorded_topic_messages':dict(counts),'last_before_finish':details,'unique_pre_finish_task_cloud_voxels':{k:len(v) for k,v in arrays.items()},'missing_internal_state':'No actual viewpoint or per-cell status stream in original bag. Approximate 9.6m spatial buckets in history are not actual cell indices.'}
print(json.dumps(summary,indent=2));(root/'TASK_CLOUD_DIAGNOSTICS.json').write_text(json.dumps(summary,indent=2));(windows/'TASK_CLOUD_DIAGNOSTICS.json').write_text(json.dumps(summary,indent=2))
