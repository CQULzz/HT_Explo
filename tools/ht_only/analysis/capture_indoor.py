from pathlib import Path
import json,time
import rclpy
from rclpy.node import Node
from rclpy.serialization import serialize_message
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from grid_map_msgs.msg import GridMap
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
root=Path('/home/lzz/ht_only_20261111/analysis/live_indoor_stop');root.mkdir(exist_ok=False)
rclpy.init();node=Node('ht_only_readonly_snapshot');received={};odom=[]
def keep(topic,msg):received[topic]=msg
node.create_subscription(Odometry,'/state_estimation',lambda m:odom.append(m),qos_profile_sensor_data)
for topic,cls in [('/ht_traversability/global_local',GridMap),('/terrain_map',PointCloud2),('/way_point',PointStamped),('/ht_minimal/local_selection',String)]:node.create_subscription(cls,topic,lambda m,t=topic:keep(t,m),10)
deadline=time.monotonic()+6
while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.05)
for topic,msg in received.items():(root/(topic.rsplit('/',1)[-1]+'.cdr')).write_bytes(serialize_message(msg))
grid=received['/ht_traversability/global_local'];stamp=lambda m:m.header.stamp.sec+m.header.stamp.nanosec*1e-9
gridtime=stamp(grid);pose=min(odom,key=lambda m:abs(stamp(m)-gridtime));(root/'state_estimation.cdr').write_bytes(serialize_message(pose))
(root/'META.json').write_text(json.dumps({'source_stamp':gridtime,'odom_delta_s':stamp(pose)-gridtime,'capture_clock':node.get_clock().now().nanoseconds/1e9,'selection':json.loads(received['/ht_minimal/local_selection'].data)},indent=2))
node.destroy_node();rclpy.shutdown();print(root)
