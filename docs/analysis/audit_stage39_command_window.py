from pathlib import Path
import argparse,json,hashlib
import rosbag2_py
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();origin=json.loads((a.trial/'current/measurement_started.json').read_text())['wall_time'];event=497.82539892196655;rows=[]
r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(a.trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=['/cmd_vel','/ht_follower_status']))
while r.has_next():
 topic,data,ns=r.read_next();t=ns/1e9-origin
 if t>event+1.5:break
 if t<event-.3:continue
 if topic=='/cmd_vel':
  m=deserialize_message(data,TwistStamped);rows.append(dict(t_s=t,topic=topic,v=m.twist.linear.x,w=m.twist.angular.z))
 else:rows.append(dict(t_s=t,topic=topic,status=deserialize_message(data,String).data))
next_zero=next((x for x in rows if x['topic']=='/cmd_vel' and x['t_s']>=event and abs(x['v'])<1e-9 and abs(x['w'])<1e-9),None)
a.output.write_text(json.dumps(dict(source=str(a.trial.resolve()),event_s=event,geometry_summary=json.loads((a.trial/'execution_geometry_audit/summary.json').read_text()),next_zero=next_zero,delay_to_next_zero_s=next_zero['t_s']-event if next_zero else None,rows=rows,limitations='Bag publication/arrival order, not exact follower callback snapshot. Constant-Twist forward projection can disagree with later commands. No continuous physical safety claim.'),indent=2)+'\n');print(next_zero);print([x for x in rows if x.get('status','').startswith('GEOMETRY')])
