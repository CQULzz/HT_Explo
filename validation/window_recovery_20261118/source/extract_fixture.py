from pathlib import Path
import json,hashlib,rosbag2_py
r=Path('/home/lzz/ht_window_recovery_20261118/analysis');old=Path('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01')
b=rosbag2_py.SequentialReader();b.open(rosbag2_py.StorageOptions(uri=str(old/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));b.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local']))
while b.has_next():_,data,t=b.read_next()
(r/'campus_stop.cdr').write_bytes(data)
(r/'FIXTURE.json').write_text(json.dumps({'source_bag':str(old/'bag'),'topic':'/ht_traversability/global_local','receipt_ns':t,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)},indent=2));print('fixture saved',len(data))
