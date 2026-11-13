from pathlib import Path
import json,sys,importlib.util
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from std_msgs.msg import String
r=Path('/home/lzz/ht_repeat_20261114/runs/repeat_02')
spec=importlib.util.spec_from_file_location('audit','/home/lzz/HT_Explo_execution_20261113/tools/cmu_minimal/audit_commands.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
def reader(topics):
    rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(r/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=topics));return rd
start=json.loads((r/'observations/START.json').read_text())['clock']
import csv
end=float(list(csv.DictReader((r/'observations/metrics.csv').open()))[-1]['time'])
rd=reader(['/ht_traversability/global_local','/ht_minimal/command_audit']);stamps={};commands=[]
while rd.has_next():
    topic,data,t=rd.read_next()
    if topic=='/ht_traversability/global_local':
        msg=deserialize_message(data,GridMap);s=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9;stamps[a.key(s)]=s
    else:
        d=json.loads(deserialize_message(data,String).data)
        if start<=d['time']<=end:commands.append(d)
unmatched=[d for d in commands if a.key(d['map_stamp']) not in stamps]
matches=[];needed={}
for d in unmatched:
    s=min(stamps.values(),key=lambda s:abs(s-d['map_stamp']));delta=s-d['map_stamp']
    matches.append({'command':d,'nearest_map_stamp':s,'delta_s':delta})
    if abs(delta)<=1e-6:needed[a.key(s)]=None
rd=reader(['/ht_traversability/global_local'])
while rd.has_next():
    topic,data,t=rd.read_next();msg=deserialize_message(data,GridMap);s=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
    if a.key(s) in needed:needed[a.key(s)]=a.decode(msg)
for m in matches:
    d=m['command'];grid=needed.get(a.key(m['nearest_map_stamp']))
    m['map_available_within_1us']=grid is not None
    if grid is not None and d['allowed']:
        ok,reason,score=a.check(grid,d);m.update(independent_passed=bool(ok),reason=reason,score=score)
result={'unmatched_by_original_rounded_key':len(unmatched),'records':matches,'all_supplemented':len(unmatched)==13 and all(m.get('map_available_within_1us') and (not m['command']['allowed'] or m.get('independent_passed')) for m in matches),'note':'Original failed audit retained. Supplement uses unique recorded source stamps within 1 microsecond only, with unchanged gate checks.'}
(r/'AUDIT_ASSOCIATION_SUPPLEMENT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
