from pathlib import Path
import json,math
import rosbag2_py
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import PointStamped
from nav_msgs.msg import Odometry
r=Path('/home/lzz/ht_campus_pcd_20261114/runs/user_pcd_600s_01');rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(r/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=['/way_point','/state_estimation']))
last=None;bad=[];count=0
while rd.has_next():
    topic,data,t=rd.read_next()
    if topic=='/state_estimation':
        m=deserialize_message(data,Odometry);p=m.pose.pose.position;last={'x':p.x,'y':p.y,'z':p.z,'stamp':m.header.stamp.sec+m.header.stamp.nanosec*1e-9}
    else:
        count+=1;m=deserialize_message(data,PointStamped);p=m.point
        if not all(math.isfinite(v) for v in [p.x,p.y,p.z]):bad.append({'record_time_ns':t,'stamp':m.header.stamp.sec+m.header.stamp.nanosec*1e-9,'x':repr(p.x),'y':repr(p.y),'z':repr(p.z),'last_finite_odometry':last})
(r/'NONFINITE_WAYPOINTS.json').write_text(json.dumps({'waypoint_count':count,'bad_waypoints':bad,'scope':'Exact recorded PointStamped values; no navigation data modified.'},indent=2));print(json.dumps(bad,indent=2))
