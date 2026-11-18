from pathlib import Path
import json,ast
r=Path('/home/lzz/tare_native_campus_20261118');w=Path('/mnt/d/TARE-Native-Campus-20261118')
# Preserve a compact terminal snapshot for passive geometry investigation after runs.
s='''from pathlib import Path
import json,rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PointStamped
import numpy as np
root=Path(ROOT_VALUE);run=root/'runs'/CASE_VALUE
reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));topics=['/terrain_map','/terrain_map_ext','/registered_scan','/state_estimation','/way_point','/path'];reader.set_filter(rosbag2_py.StorageFilter(topics=topics));last={}
while reader.has_next():
 topic,data,t=reader.read_next();last[topic]=(data,t)
out=run/'terminal_inputs';out.mkdir(exist_ok=True);index={}
for topic,(data,t) in last.items():
 name=topic.strip('/')+'.cdr';(out/name).write_bytes(data);index[topic]={'file':name,'receipt_ns':t,'bytes':len(data)}
 if topic in ['/terrain_map','/terrain_map_ext','/registered_scan']:
  m=deserialize_message(data,PointCloud2);fields={f.name:f.offset for f in m.fields};names=[n for n in ['x','y','z','intensity'] if n in fields];dtype=np.dtype({'names':names,'formats':['<f4']*len(names),'offsets':[fields[n] for n in names],'itemsize':m.point_step});array=np.ndarray((m.height,m.width),dtype=dtype,buffer=m.data,strides=(m.row_step,m.point_step));np.savez_compressed(out/(topic.strip('/')+'.npz'),**{n:array[n].ravel() for n in names},stamp_s=m.header.stamp.sec+m.header.stamp.nanosec*1e-9,frame_id=m.header.frame_id)
(out/'INDEX.json').write_text(json.dumps(index,indent=2));print('Terminal raw inputs saved',run)
'''
for tag,root,case in [('first',str(r),'native_campus_01'),('repeat','/home/lzz/tare_native_campus_repeat_20261118','native_campus_02')]:
 text=s.replace('ROOT_VALUE',repr(root)).replace('CASE_VALUE',repr(case));(w/(tag+'_extract_terminal.py')).write_text(text);ast.parse(text)
print('Prepared terminal native terrain/pose/path snapshot extraction for post-run only')
