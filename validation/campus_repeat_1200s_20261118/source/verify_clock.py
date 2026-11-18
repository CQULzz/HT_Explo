from pathlib import Path
import json,csv
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosgraph_msgs.msg import Clock
r=Path('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01');start=json.loads((r/'observations/START.json').read_text())['clock'];end=float(list(csv.DictReader((r/'observations/metrics.csv').open()))[-1]['time']);rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(r/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=['/clock']));samples=[]
while rd.has_next():
 topic,data,t=rd.read_next()
 if start<=t/1e9<=end:
  m=deserialize_message(data,Clock);samples.append([t/1e9,m.clock.sec+m.clock.nanosec*1e-9])
samples.sort();a=json.loads((r/'ANALYSIS.json').read_text());a['sim_time_advanced_s']=samples[-1][1]-samples[0][1];a['sim_real_time_factor']=a['sim_time_advanced_s']/(samples[-1][0]-samples[0][0]);a['clock_samples']=len(samples);a['clock_receipt_span_s']=samples[-1][0]-samples[0][0];a['clock_aggregation']='Chronological bag receipts, independent of lexicographic MCAP filenames';(r/'ANALYSIS.json').write_text(json.dumps(a,indent=2));print(json.dumps({k:a[k] for k in ['sim_time_advanced_s','sim_real_time_factor','clock_samples','clock_receipt_span_s']}))
p=Path('/mnt/d/HT-Campus-1200s-20261118/postprocess_long.py');s=p.read_text();s=s.replace('if len(clock_samples)>1:','clock_samples.sort()\nif len(clock_samples)>1:');p.write_text(s)
