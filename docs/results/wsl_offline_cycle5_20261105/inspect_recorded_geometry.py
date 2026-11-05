from pathlib import Path
import json,math,hashlib
import numpy as np
from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
R=Path('/home/w_lzz/ht-iterations-20261105');P=R/'repo';run=R/'cycle2/queue_seed99_c04';rows=[];pose=None
for bag in sorted((run/'bag').glob('*.mcap')):
 with bag.open('rb') as stream:
  for schema,channel,msg in make_reader(stream,validate_crcs=True).iter_messages(topics=['/ht_real/odometry','/ht_real/collision_cloud'],log_time_order=True):
   if channel.topic=='/ht_real/odometry':
    odom=deserialize_message(msg.data,Odometry);p=odom.pose.pose.position;pose=np.array([p.x,p.y,p.z]);continue
   if pose is None:continue
   cloud=deserialize_message(msg.data,PointCloud2)
   if cloud.header.frame_id!='map':continue
   points=read_points_numpy(cloud,field_names=['x','y','z'],skip_nans=True)
   in_z=points[np.abs(points[:,2]-pose[2])<=.5]
   if not len(in_z):continue
   xy=np.linalg.norm(in_z[:,:2]-pose[:2],axis=1);i=int(xy.argmin());radius=.7+.5*math.hypot(.2,.2)
   rows.append({'cloud_source_s':cloud.header.stamp.sec+cloud.header.stamp.nanosec/1e9,'recorded_delivery_log_ns':msg.log_time,'recorded_latest_odometry_source_s':odom.header.stamp.sec+odom.header.stamp.nanosec/1e9,'pose_xyz':pose.tolist(),'nearest_z_eligible_point_xyz':in_z[i].tolist(),'nearest_xy_m':float(xy[i]),'configured_cylinder_radius_m':radius,'inside_existing_cylinder':bool(xy[i]<=radius+1e-7),'point_count':len(points)})
out={'scope':'Read-only stored collision clouds, paired with most recent odometry at recorder delivery. This is not the exact follower callback order or independent scene/ground-truth collision certification. No ROS node, playback, controller or simulation. Fixed existing envelope: margin0.7 + half-diagonal(0.2,0.2), z +/-0.5.','source_run':str(run),'latest_10_pairs':rows[-10:],'tracked_config_sha256':{str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [P/'src/ht_scout_bridge/config/tare_scout.yaml',P/'src/tare_planner/include/ht_cost/measured_collision_field.h']}}
dest=P/'docs/results/wsl_offline_cycle5_20261105/GEOMETRY_EVIDENCE.json';dest.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
