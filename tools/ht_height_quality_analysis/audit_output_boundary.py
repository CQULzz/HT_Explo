"""Validate outputs whose odometry header is inside but control time is outside the window."""
from pathlib import Path
import json,csv,sys
import rosbag2_py
from rclpy.serialization import deserialize_message
from std_msgs.msg import String
from grid_map_msgs.msg import GridMap
sys.path.insert(0,'/home/lzz/HT_Explo_quality_20261111/tools/cmu_minimal')
from audit_commands import decode,check,key
RUN=Path('/home/lzz/ht_quality_20261111/runs/cmu_quality_300s_01')
original=json.loads((RUN/'PUBLISHED_COMMAND_MATCH.json').read_text())
end=float(list(csv.DictReader((RUN/'observations/metrics.csv').open()))[-1]['time'])
r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(RUN/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
r.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/ht_minimal/command_audit']));r.seek(int((end-2)*1e9))
maps={};audits=[]
while r.has_next():
 topic,data,received=r.read_next()
 if received/1e9>end+.2:break
 if topic=='/ht_traversability/global_local':
  m=deserialize_message(data,GridMap);maps[key(m.header.stamp.sec+m.header.stamp.nanosec*1e-9)]=decode(m)
 else:
  d=json.loads(deserialize_message(data,String).data)
  if d['allowed']:audits.append((received/1e9,d))
results=[]
for c in original['unmatched_examples']:
 matches=[(abs(t-c['received']),d) for t,d in audits if abs(t-c['received'])<=.1 and abs(d['linear_candidate']-c['linear'])<1e-7 and abs(d['angular_candidate']-c['angular'])<1e-7]
 item={'output':c,'matched':bool(matches)}
 if matches:
  delta,d=min(matches,key=lambda x:x[0]);m=maps.get(key(d['map_stamp']));ok,reason,score=check(m,d) if m is not None else (False,'MAP_NOT_FOUND',None)
  item.update(audit=d,receive_delta_s=delta,control_time_after_window_s=d['time']-end,odometry_header_before_window_end_s=end-c['odom_stamp'],independent_pass=ok,independent_reason=reason,minimum_swept_score=score)
 results.append(item)
passed=original['all_accepted_candidates_independently_passed'] and len(results)==original['unmatched_count'] and all(x.get('independent_pass',False) for x in results)
out={'original_report_preserved':'PUBLISHED_COMMAND_MATCH.json','original_unmatched_count':original['unmatched_count'],'boundary_results':results,'published_nonzero_commands':original['published_nonzero_commands'],'matched_and_independently_checked_total':original['matched_to_accepted_audit']+sum(x.get('independent_pass',False) for x in results),'passed':passed,'scope':'Supplement only: original matcher filters outputs by their odometry-header time and audits by control time. One final output straddles the window boundary. It is associated by equal v/w within 1e-7 and receipt within 100ms, then its complete reaction/braking sweep is independently checked against the exact recorded map at its actual control time. Performance window and original failed matcher receipt are unchanged. Receipt proximity does not prove unique identity for repeated equal velocities.'}
(RUN/'OUTPUT_BOUNDARY_AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
