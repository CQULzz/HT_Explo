from pathlib import Path
import json,csv,math,importlib.util
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from std_msgs.msg import String
r=Path('/home/lzz/ht_campus_pcd_20261114/runs/user_pcd_600s_02')
spec=importlib.util.spec_from_file_location('audit','/home/lzz/HT_Explo_execution_20261113/tools/cmu_minimal/audit_commands.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
rows=list(csv.DictReader((r/'observations/metrics.csv').open()));last=rows[-1];distance=float(last['distance_m']);moving=[v for v in rows if float(v['distance_m'])<distance-.01];stop_time=float(moving[-1]['elapsed_s']) if moving else 0.
rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(r/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/ht_minimal/command_audit']))
lower=int((float(last['time'])-4)*1e9)
if hasattr(rd,'seek'):rd.seek(lower)
cache={};dlast=None
while rd.has_next():
    topic,data,t=rd.read_next()
    if t<lower:continue
    if topic=='/ht_traversability/global_local':
        msg=deserialize_message(data,GridMap);s=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9;cache[a.key(s)]=a.decode(msg)
    else:
        d=json.loads(deserialize_message(data,String).data)
        if d.get('reason')=='HT_DIRECTION_LOW' and d.get('time',0)<=float(last['time']):dlast=d
assert dlast is not None and a.key(dlast['map_stamp']) in cache
m=cache[a.key(dlast['map_stamp'])];rr=int(np.floor(m['rows']*.5-(dlast['x']-m['cx'])/m['res']));cc=int(np.floor(m['cols']*.5-(dlast['y']-m['cy'])/m['res']));ok,reason,score=a.check(m,dlast)
result={'last_moving_time_estimate_s':stop_time,'stop_position':{k:float(last[k]) for k in ['x','y','z','yaw']},'command':dlast,'center_scores_8directions':m['scores'][:,rr,cc].astype(float).tolist(),'center_context_valid':bool(m['valid'][rr,cc]>=.5),'center_raw_occupied':bool(m['raw_occupied'][rr,cc]),'independent_gate_passed':bool(ok),'independent_reason':reason,'swept_minimum_score':score,'note':'Late stationary snapshot, not claimed to be the first blocking frame or model ground-truth validation. Last movement estimate uses final distance minus 1cm with 0.5s metric samples.'}
(r/'STOP_SNAPSHOT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
