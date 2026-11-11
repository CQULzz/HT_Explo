from pathlib import Path
import json,csv
import rosbag2_py
from rclpy.serialization import deserialize_message
from std_msgs.msg import String
ROOT=Path('/home/lzz/ht_recovery_20261111');run=ROOT/'runs/cmu_recovery_300s_01';end=float(list(csv.DictReader((run/'observations/metrics.csv').open()))[-1]['time']);r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=['/ht_minimal/command_audit']));r.seek(int((end-.1)*1e9));matches=[]
while r.has_next():
 _,data,received=r.read_next()
 if received/1e9>end+.3:break
 d=json.loads(deserialize_message(data,String).data)
 if d['allowed'] and abs(d['linear_candidate']-.5000000596046448)<1e-7 and abs(d['angular_candidate']-.34107619524002075)<1e-7:matches.append({'received':received/1e9,'audit':d,'control_time_after_collection_s':d['time']-end})
result={'collection_last_sample_time':end,'matching_allowed_candidates':matches,'scope':'Supplementary boundary association. Candidate decision time outside the collection interval was deliberately excluded from the main in-window audit.'};(ROOT/'analysis/FIRST_BOUNDARY.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
