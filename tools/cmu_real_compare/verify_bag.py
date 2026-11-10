from pathlib import Path
import json,collections
import rosbag2_py
from rosidl_runtime_py.utilities import get_message
from rclpy.serialization import deserialize_message
root=Path('/home/lzz/cmu_real_compare_20261110');run=root/'runs/old_real_600s_01'
start=json.loads((run/'observations/START.json').read_text())['clock'];end=start+600.0043041369972
reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('cdr','cdr'))
topics=['/ht_real/mission_state','/ht_real/ht_execution_status','/ht_real/ht_follower_status','/cmd_vel','/ht_real/mission_completed','/ht_real/exploration_finish']
types={t.name:get_message(t.type) for t in reader.get_all_topics_and_types() if t.name in topics}
reader.set_filter(rosbag2_py.StorageFilter(topics=topics));counts=collections.Counter();first={};commands=[];status=collections.Counter()
while reader.has_next():
 topic,data,stamp=reader.read_next();t=stamp/1e9
 if not start<=t<=end:continue
 msg=deserialize_message(data,types[topic]);counts[topic]+=1
 if topic=='/ht_real/mission_state' and msg.data not in first:first[msg.data]=t-start
 if topic=='/ht_real/ht_follower_status':status[msg.data]+=1
 if topic=='/cmd_vel':commands.append((msg.header.stamp.sec+msg.header.stamp.nanosec/1e9,msg.twist.linear.x,msg.twist.angular.z))
completion=start+first['COMPLETED'];after=[m for m in commands if m[0]>completion+.1]
result={'counts':dict(counts),'first_mission_state_receipt_elapsed_s':first,'follower_status_message_counts':dict(status),'commands_after_completed_plus_100ms':len(after),'nonzero_commands_after_completed_plus_100ms':sum(abs(m[1])>1e-9 or abs(m[2])>1e-9 for m in after),'scope':'MCAP independently checked against observer; status lacks source header, so bag receipt times are used for transitions; 100ms guard excludes in-flight commands.'}
assert after and result['nonzero_commands_after_completed_plus_100ms']==0
(root/'delivery/BAG_STATE_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
