from pathlib import Path
import json,hashlib
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
run=Path('/home/lzz/ht_labels_repeat_20261117/runs/explicit_labels_campus_repeat_01')
dest=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/labels_repeat_20261117/data')
rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local']))
first=last=None;count=0
while rd.has_next():
 topic,data,t=rd.read_next();count+=1
 if first is None:first=(data,t)
 last=(data,t)
index={'source_bag':str(run/'bag'),'topic':'/ht_traversability/global_local','maps_read':count,'representation':'Raw recorded HT layers; ring-buffer indices normalized. No execution prior or persistent actual-label state applied.','snapshots':[]}
for name,(data,t) in [('first',first),('last',last)]:
 m=deserialize_message(data,GridMap);rows=round(m.info.length_x/m.info.resolution);cols=round(m.info.length_y/m.info.resolution)
 layers={n:np.roll(np.asarray(a.data,np.float32).reshape((rows,cols),order='F'),(-m.outer_start_index,-m.inner_start_index),(0,1)) for n,a in zip(m.layers,m.data)}
 f=dest/('ht_map_'+name+'.npz');np.savez_compressed(f,**layers)
 index['snapshots'].append({'file':f.name,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'stamp_s':m.header.stamp.sec+m.header.stamp.nanosec*1e-9,'bag_receipt_ns':t,'frame_id':m.header.frame_id,'rows':rows,'cols':cols,'resolution_m':m.info.resolution,'center_xyz':[m.info.pose.position.x,m.info.pose.position.y,m.info.pose.position.z],'orientation_xyzw':[m.info.pose.orientation.x,m.info.pose.orientation.y,m.info.pose.orientation.z,m.info.pose.orientation.w],'layers':m.layers,'axis_convention':'world_x=cx+(rows/2-row-0.5)*res, world_y=cy+(cols/2-col-0.5)*res'})
(dest/'MAP_SNAPSHOTS.json').write_text(json.dumps(index,indent=2));print(json.dumps({'maps':count,'files':[{k:s[k] for k in ['file','bytes','sha256']} for s in index['snapshots']]}))
