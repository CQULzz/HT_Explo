"""Compare the same recorded map/command under both envelopes (1 Hz sample)."""
from pathlib import Path
import importlib.util, json,collections,math
import numpy as np
import rosbag2_py
from grid_map_msgs.msg import GridMap
from std_msgs.msg import String
from rclpy.serialization import deserialize_message
import sys
script=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/tools/cmu_minimal/audit_commands.py')
spec=importlib.util.spec_from_file_location('gate_audit',script);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
root=Path('/home/lzz/ht_urdf_compare_20261115');env=json.loads((root/'setup/URDF_ENVELOPE.json').read_text());out=Path('/mnt/d/HT-URDF-Compare-20261115/analysis');out.mkdir(exist_ok=True)
results=[]
for variant in ['baseline','urdf']:
    run=root/'runs'/f'{variant}_campus_600s_01';start=json.loads((run/'observations/START.json').read_text())['clock']
    end=start+json.loads((run/'RESULT.json').read_text())['summary']['elapsed_s']
    rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    rd.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/ht_minimal/command_audit']))
    cache=collections.OrderedDict();decoded={};pending=[];seen=set();counts=collections.Counter();examples=[]
    def process(d):
        key=round(d['map_stamp']*1e6)
        if key not in cache:return False
        if not start<=d['time']<=end or not d['allowed'] or (abs(d['linear_candidate'])<1e-8 and abs(d['angular_candidate'])<1e-8):return True
        second=int(d['time']-start)
        if second in seen:return True
        seen.add(second);checks=[]
        for target,radius in [('old',.45),('urdf',env['required_support_radius'])]:
            ck=(key,target)
            if ck not in decoded:audit.RADIUS=radius;decoded[ck]=audit.decode(cache[key])
            item=dict(d);item.update(obstacle_footprint='oriented_box_v1' if target=='old' else 'urdf_box_xy_v1',body_length=.6 if target=='old' else env['size_xyz'][0],body_width=.6 if target=='old' else env['size_xyz'][1],body_center_x=0 if target=='old' else env['center_xyz'][0],body_center_y=0 if target=='old' else env['center_xyz'][1],support_radius=radius)
            audit.RADIUS=radius;ok,reason,score=audit.check(decoded[ck],item);checks.append((ok,reason,score))
        counts['sampled_moving_commands']+=1
        counts[f'old_{checks[0][0]}_urdf_{checks[1][0]}']+=1
        if checks[0][0] and not checks[1][0]:
            counts['new_rejection_'+checks[1][1]]+=1
            if len(examples)<15:examples.append({'time':d['time']-start,'x':d['x'],'y':d['y'],'yaw':d['yaw'],'v':d['linear_candidate'],'w':d['angular_candidate'],'reason':checks[1][1]})
        return True
    while rd.has_next():
        topic,data,t=rd.read_next()
        if topic=='/ht_traversability/global_local':
            msg=deserialize_message(data,GridMap);key=round((msg.header.stamp.sec+msg.header.stamp.nanosec/1e9)*1e6);cache[key]=msg
            if len(cache)>24:
                oldkey,_=cache.popitem(last=False)
                for target in ['old','urdf']:decoded.pop((oldkey,target),None)
            pending=[d for d in pending if not process(d)]
        else:
            d=json.loads(deserialize_message(data,String).data)
            if start<=d['time']<=end and not process(d):pending.append(d)
    missing=sum(d['allowed'] and (abs(d['linear_candidate'])>1e-8 or abs(d['angular_candidate'])>1e-8) for d in pending)
    result={'variant_recording':variant,'scope':'First allowed moving candidate each elapsed second; same recorded HT map and braking sweep under both envelopes. Counterfactual, not an additional closed-loop run. Larger known-ground circle is included.','counts':dict(counts),'unmatched_moving_records':missing,'examples':examples};results.append(result);print(json.dumps(result,indent=2),flush=True)
(out/'SAME_MAP_ENVELOPE_COMPARISON.json').write_text(json.dumps(results,indent=2))
