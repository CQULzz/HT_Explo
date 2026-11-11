from pathlib import Path
import json
import rosbag2_py
from rclpy.serialization import deserialize_message
from std_msgs.msg import String
from geometry_msgs.msg import TwistStamped
root=Path('/home/lzz/ht_only_20261111');run=root/'runs/a_user_pcd_600s_02';target=1794363551.7840695;r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=['/cmd_vel','/ht_minimal/command_audit']));r.seek(int((target-1)*1e9));records=[]
while r.has_next():
 topic,data,received=r.read_next()
 if received/1e9>target+1:break
 if topic=='/ht_minimal/command_audit':d=json.loads(deserialize_message(data,String).data)
 else:
  m=deserialize_message(data,TwistStamped);d={'header_stamp':m.header.stamp.sec+m.header.stamp.nanosec*1e-9,'linear':m.twist.linear.x,'angular':m.twist.angular.z}
 records.append({'topic':topic,'received':received/1e9,'data':d})
(root/'analysis/UNMATCHED_COMMAND_WINDOW.json').write_text(json.dumps(records,indent=2));matches=[]
for m in records:
 if m['topic']!='/ht_minimal/command_audit':continue
 d=m['data']
 if abs(d['linear_candidate']-.4750000536441803)<1e-7 and abs(d['angular_candidate']-5.7032342738239095e-05)<1e-7:matches.append(m)
print('same-velocity candidates',json.dumps(matches,indent=2))
