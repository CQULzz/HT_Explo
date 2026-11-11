"""Supplement unmatched output associations at measurement-window boundaries."""
from pathlib import Path
import csv,json,sys
import rosbag2_py
from rclpy.serialization import deserialize_message
from std_msgs.msg import String
from grid_map_msgs.msg import GridMap
sys.path.insert(0,'/home/lzz/HT_Explo_quality_20261111/tools/cmu_minimal')
from audit_commands import decode,check,key
RUN=Path('/home/lzz/ht_quality_600s_20261112/runs/cmu_quality_600s_02')
original=json.loads((RUN/'PUBLISHED_COMMAND_MATCH.json').read_text())
rows=list(csv.DictReader((RUN/'observations/metrics.csv').open()));end=float(rows[-1]['time'])
start=json.loads((RUN/'observations/START.json').read_text())['clock'];results=[]
for output in original['unmatched_examples']:
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(RUN/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/ht_minimal/command_audit']))
    reader.seek(int((output['received']-2)*1e9));maps={};audits=[]
    while reader.has_next():
        topic,data,received=reader.read_next()
        if received/1e9>output['received']+.2:break
        if topic=='/ht_traversability/global_local':
            msg=deserialize_message(data,GridMap);maps[key(msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9)]=decode(msg)
        else:
            d=json.loads(deserialize_message(data,String).data)
            if d['allowed']:audits.append((received/1e9,d))
    possible=[(abs(t-output['received']),d) for t,d in audits if abs(t-output['received'])<=.1 and abs(d['linear_candidate']-output['linear'])<1e-7 and abs(d['angular_candidate']-output['angular'])<1e-7]
    item={'output':output,'matched':bool(possible)}
    if possible:
        delta,d=min(possible,key=lambda x:x[0]);m=maps.get(key(d['map_stamp']));ok,reason,score=check(m,d) if m is not None else (False,'MAP_NOT_FOUND',None)
        # A supplemental association must actually explain the window mismatch.
        outside=not start<=d['time']<=end
        item.update(audit=d,receive_delta_s=delta,control_time_outside_original_window=outside,control_time_after_end_s=d['time']-end,independent_pass=ok and outside,independent_reason=reason,minimum_swept_score=score)
    results.append(item)
passed=original['all_accepted_candidates_independently_passed'] and len(results)==original['unmatched_count'] and all(x.get('independent_pass',False) for x in results)
out={'original_report_preserved':'PUBLISHED_COMMAND_MATCH.json','original_unmatched_count':original['unmatched_count'],'boundary_results':results,'published_nonzero_commands':original['published_nonzero_commands'],'matched_and_independently_checked_total':original['matched_to_accepted_audit']+sum(x.get('independent_pass',False) for x in results),'passed':passed,'scope':'Keep original output-header and audit-control windows and receipts. Supplement only boundary associations with equal v/w within 1e-7 and receipt within 100ms, then independently check their exact original-map reaction/braking sweep at actual control time. No performance-window extension. Receipt association need not be unique for repeated equal velocities.'}
(RUN/'OUTPUT_BOUNDARY_AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
