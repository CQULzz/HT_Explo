"""Link recorded nonzero outputs to independently checked accepted gate candidates."""
from pathlib import Path
import argparse,json,bisect
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String
ap=argparse.ArgumentParser();ap.add_argument('run',type=Path);a=ap.parse_args();start=json.loads((a.run/'observations/START.json').read_text())['clock'];import csv
end=float(list(csv.DictReader((a.run/'observations/metrics.csv').open()))[-1]['time']);audits=[];commands=[]
r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(a.run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=['/cmd_vel','/ht_minimal/command_audit']))
while r.has_next():
 topic,data,received=r.read_next()
 if topic=='/ht_minimal/command_audit':
  d=json.loads(deserialize_message(data,String).data)
  if d['allowed'] and start<=d['time']<=end:audits.append((received/1e9,d))
 else:
  m=deserialize_message(data,TwistStamped);stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
  if start<=stamp<=end and abs(m.twist.linear.x)+abs(m.twist.angular.z)>1e-8:commands.append((received/1e9,stamp,m.twist.linear.x,m.twist.angular.z))
audits.sort(key=lambda x:x[0]);times=[x[0] for x in audits];unmatched=[];deltas=[];pairs=[];lags=[]
for received,stamp,v,w in commands:
 lo=bisect.bisect_left(times,received-.1);hi=bisect.bisect_right(times,received+.1);possible=[(abs(t-received),d) for t,d in audits[lo:hi] if abs(d['linear_candidate']-v)<1e-7 and abs(d['angular_candidate']-w)<1e-7]
 if not possible:unmatched.append({'received':received,'odom_stamp':stamp,'linear':v,'angular':w});continue
 delta,d=min(possible,key=lambda x:x[0]);deltas.append(delta);lags.append(d['time']-stamp);pairs.append([received,stamp,v,w,d['time'],d['map_stamp']])
independent=json.loads((a.run/'COMMAND_AUDIT.json').read_text());result={'published_nonzero_commands':len(commands),'matched_to_accepted_audit':len(pairs),'unmatched_count':len(unmatched),'unmatched_examples':unmatched[:20],'maximum_receive_time_delta_s':max(deltas,default=None),'maximum_control_minus_odometry_stamp_s':max(lags,default=None),'outputs_with_odometry_header_lag_gt_150ms':sum(v>.15 for v in lags),'all_accepted_candidates_independently_passed':independent['passed'],'passed':bool(commands) and not unmatched and independent['passed'],'scope':'Equal linear/angular values within 1e-7, nearby bag receipt within 100ms; odometry-header lag is recorded separately, not used to reject velocity associations. Every matched accepted candidate has been checked independently against its exact HT map by COMMAND_AUDIT.json. Receipt proximity does not uniquely identify a publish when identical velocities repeat.'}
(a.run/'PUBLISHED_COMMAND_MATCH.json').write_text(json.dumps(result,indent=2));np.savez_compressed(a.run/'published_command_pairs.npz',pairs=np.array(pairs));print(json.dumps(result,indent=2))
