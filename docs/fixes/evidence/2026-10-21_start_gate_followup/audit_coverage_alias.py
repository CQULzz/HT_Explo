"""Read-only last-state coverage lattice audit for a sealed run."""
import argparse,json
from pathlib import Path
import numpy as np,yaml,rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
ap=argparse.ArgumentParser();ap.add_argument('trial',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();p=a.trial
r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(p/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=['/state_estimation','/viewpoint_vis_cloud','/viewpoint_in_collision_cloud_','/ht_execution_rejected_edge']))
last={};counts={}
while r.has_next():
 t,b,ns=r.read_next();last[t]=(b,ns);counts[t]=counts.get(t,0)+1
odom=deserialize_message(last['/state_estimation'][0],Odometry);q=np.array([odom.pose.pose.position.x,odom.pose.pose.position.y]);cfg=yaml.safe_load((p/'planner_parameters.yaml').read_text())['/tare_planner_node']['ros__parameters'];res=np.array([cfg['viewpoint_manager/resolution_x'],cfg['viewpoint_manager/resolution_y']]);clouds={}
for name in ['/viewpoint_vis_cloud','/viewpoint_in_collision_cloud_']:
 msg=deserialize_message(last[name][0],PointCloud2);clouds[name]=np.asarray(point_cloud2.read_points_numpy(msg,field_names=('x','y','z'),skip_nans=True),float)
anchor=clouds['/viewpoint_vis_cloud'][0,:2];center=anchor+np.round((q-anchor)/res)*res
result=dict(robot_xy=q.tolist(),coverage_resolution_xy=res.tolist(),nearest_coverage_center_xy=center.tolist(),candidate_count=len(clouds['/viewpoint_vis_cloud']),center_in_candidates=bool(np.any(np.linalg.norm(clouds['/viewpoint_vis_cloud'][:,:2]-center,axis=1)<1e-4)),center_in_collision_labels=bool(np.any(np.linalg.norm(clouds['/viewpoint_in_collision_cloud_'][:,:2]-center,axis=1)<1e-4)),message_counts=counts,record_times={k:v[1] for k,v in last.items()},scope='Offline final stationary odometry and coverage-cloud lattice. Continuous root differs from closest0.3m coverage center; callback timing is not replayed. Position inside full grid and height require source/unit-regression checks.')
if '/ht_execution_rejected_edge' in last:result['last_rejection_age_s']=(last['/state_estimation'][1]-last['/ht_execution_rejected_edge'][1])/1e9
a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
