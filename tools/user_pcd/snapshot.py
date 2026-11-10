from pathlib import Path
import sys,json,time,math
sys.path.insert(0,'/home/lzz/HT_Explo_pcd_20261110/tools/cmu_minimal')
from audit_commands import decode
import numpy as np,rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.serialization import serialize_message
from nav_msgs.msg import Odometry
from grid_map_msgs.msg import GridMap
root=Path('/home/lzz/pcd_test_20261110/delivery');rclpy.init();n=Node('recorded_map_readonly_snapshot');last={}
n.create_subscription(Odometry,'/state_estimation',lambda m:last.update(odom=m),qos_profile_sensor_data)
n.create_subscription(GridMap,'/ht_traversability/global_local',lambda m:last.update(map=m),1)
deadline=time.monotonic()+15
while time.monotonic()<deadline:
 rclpy.spin_once(n,timeout_sec=.1)
 if len(last)==2:break
else:raise RuntimeError('Snapshot inputs absent')
m=last['map'];odom=last['odom'];d=decode(m);p=odom.pose.pose.position;q=odom.pose.pose.orientation;yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
r=int(np.floor(d['rows']*.5-(p.x-d['cx'])/d['res']));c=int(np.floor(d['cols']*.5-(p.y-d['cy'])/d['res']));channel=int(np.floor(((yaw+2*math.pi)%(2*math.pi))/(math.pi/4)+.5))%8
now=n.get_clock().now().nanoseconds/1e9;stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
result={'snapshot_clock':now,'map_stamp':stamp,'map_source_age_s':now-stamp,'position':[p.x,p.y,p.z],'yaw_rad':yaw,'yaw_deg':math.degrees(yaw),'current_channel':channel,'current_score':float(d['scores'][channel,r,c]),'eight_scores_at_robot':d['scores'][:,r,c].astype(float).tolist(),'current_physical_missing':bool(d['missing'][r,c]),'current_physical_occupied':bool(d['occupied'][r,c]),'current_context_valid':bool(d['valid'][r,c]>=.5),'scope':'Later stationary snapshot; not a reconstruction of the first stopping instant. Scores are model predictions, not labelled terrain truth.'}
(root/'STATIONARY_SNAPSHOT.json').write_text(json.dumps(result,indent=2));(root/'STATIONARY_MAP.cdr').write_bytes(serialize_message(m))
np.savez_compressed(root/'stationary_map.npz',scores=d['scores'],valid=d['valid'],missing=d['missing'],occupied=d['occupied'],cx=d['cx'],cy=d['cy'],res=d['res'])
print(json.dumps(result,indent=2));n.destroy_node();rclpy.shutdown()
