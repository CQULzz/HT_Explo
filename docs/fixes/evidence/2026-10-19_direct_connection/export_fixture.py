from pathlib import Path
import argparse,json,re,hashlib
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from grid_map_msgs.msg import GridMap
from sensor_msgs_py import point_cloud2
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--time',type=float,default=195);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);origin=json.load(open(a.trial/'current/measurement_started.json'))['wall_time'];lines=(a.trial/'current/tare.log').read_text(errors='replace').splitlines();searches=[]
for l in lines:
 if 'HT_SEARCH_AUDIT ' not in l:continue
 m=re.search(r'\[INFO\] \[([0-9.]+)\]',l)
 if m:
  d=dict(re.findall(r'(\w+)=([^ ]+)',l.split('HT_SEARCH_AUDIT ',1)[1]));d.update(log=l,t_s=float(m[1])-origin);searches.append(d)
chosen=min(searches,key=lambda d:abs(d['t_s']-a.time));target_stamp=float(chosen['ht_stamp']);target_time=origin+chosen['t_s'];topics=['/state_estimation','/ht_traversability/global_local','/collision_cloud','/viewpoint_in_collision_cloud_','/viewpoint_vis_cloud'];latest={};ht=None
reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(a.trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
while reader.has_next():
 topic,raw,ns=reader.read_next()
 if ns/1e9>target_time:break
 if topic=='/ht_traversability/global_local':
  msg=deserialize_message(raw,GridMap);stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
  if abs(stamp-target_stamp)<1e-6:ht=(raw,ns,stamp)
 else:latest[topic]=(raw,ns)
assert ht and all(t in latest for t in topics if not t.startswith('/ht_'))
(a.output/'ht_map.cdr').write_bytes(ht[0]);m=deserialize_message(latest['/state_estimation'][0],Odometry);q=m.pose.pose.orientation;pos=m.pose.pose.position;robot=[pos.x,pos.y,pos.z,float(np.arctan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))];meta={}
for t,(raw,ns) in latest.items():
 if t=='/state_estimation':continue
 m=deserialize_message(raw,PointCloud2);v=point_cloud2.read_points(m,field_names=['x','y','z','intensity'],skip_nans=True);array=np.column_stack([v[k] for k in ['x','y','z','intensity']]);np.savetxt(a.output/(t.strip('/')+'.csv'),array,delimiter=',',header='x,y,z,intensity',comments='',fmt='%.10g');meta[t]=dict(recorded_time_s=ns/1e9-origin,stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9,frame=m.header.frame_id,points=len(array))
(a.output/'metadata.json').write_text(json.dumps(dict(trial=str(a.trial.resolve()),chosen_search=chosen,robot=robot,ht_source_stamp=ht[2],ht_received_time_s=ht[1]/1e9-origin,messages=meta,limitations='Exact logged HT source stamp; latest recorded clouds/odom before post-search log. Bag arrival ordering does not reconstruct the planner callback order or exact rolling origin. Static stopped interval reduces motion mismatch but is not exact-state replay.'),indent=2)+'\n');print(json.dumps(dict(robot=robot,chosen=chosen,clouds=meta),indent=2))
