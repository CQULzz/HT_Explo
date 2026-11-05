from pathlib import Path
import sys,json,numpy as np
from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
R=Path('/home/w_lzz/ht-iterations-20261105/cycle6');classes={name:get_message(name) for name in ['rosgraph_msgs/msg/Clock','grid_map_msgs/msg/GridMap']}
for label in sys.argv[1:]:
 out=R/label;lastclock=None;ages=[];missing=0
 for path in sorted((out/'bag').glob('*.mcap')):
  with path.open('rb') as f:
   for schema,ch,msg in make_reader(f,validate_crcs=True).iter_messages(log_time_order=True):
    if ch.topic=='/clock':
     m=deserialize_message(msg.data,classes[schema.name]);lastclock=m.clock.sec*10**9+m.clock.nanosec
    elif ch.topic=='/ht_real/traversability':
     m=deserialize_message(msg.data,classes[schema.name]);stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
     if lastclock is None:missing+=1
     else:ages.append((lastclock-stamp)/1e9)
 result={'scope':'Additional full-rate recorded HT source age against most recently received ROS clock at recorder delivery, including transport/clock sampling; distinct from the unchanged primary 1Hz producer performance metric. Not pure publication latency.','count':len(ages),'missing_clock':missing,'negative_age_count':sum(x<0 for x in ages),'quantiles_s':dict(zip(['p50','p95','max'],map(float,np.percentile(ages,[50,95,100])))) if ages else None,'over_1s':sum(x>1 for x in ages)}
 (out/'DELIVERY_AGE.json').write_text(json.dumps(result,indent=2));print(label,json.dumps(result))
