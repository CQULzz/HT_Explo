from pathlib import Path
import os,sys,json,pickle,sqlite3,hashlib,shutil
import numpy as np
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');P=Path('/media/lzz/My Passport/HT_filter_expansion_2026-10-29');O=Path(__file__).parent
role=sys.argv[1];assert role in ['original_stationary','plus20_stationary'];source=B/'rebuild_165317' if role=='original_stationary' else P/'pad020_165317';C=Path('/home/lzz/my test')/('HT_multigroup_contexts_'+role+'_20261029');assert not C.exists();C.mkdir();os.environ['HT_CONTEXT_DUMP']=str(C);sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
import rclpy
from rclpy.time import Time
from rclpy.duration import Duration
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer
from types import SimpleNamespace
from scipy.spatial.transform import Rotation
from cupy_to_ht import CupyToHt
from inference_context_io import ContextCaptureSchedule
from replay_real_archive import layers
from replay_newbags_rviz import matrix
rclpy.init(args=['--ros-args','-p','ht_device:=cuda','-p','ht_quality_backend:=numba','-p','surface_sensor_ground_offset_m:=0.23479','-p','odometry_child_frame:=base_link','-p','ht_small_hole_repair:=true']);n=CupyToHt();n.context_schedule=ContextCaptureSchedule(warmup_s=1e9,interval_s=0.);clock=[0];n.get_clock=lambda:SimpleNamespace(now=lambda:Time(nanoseconds=clock[0]));messages=[];n.pub=SimpleNamespace(publish=messages.append,get_subscription_count=lambda:0);n.history_pub=SimpleNamespace(get_subscription_count=lambda:0)
buf=Buffer(cache_time=Duration(seconds=180.));db=next((B/'inputs/rosbag2_2026_10_28-16_53_17/rosbag2_2026_10_28-16_53_17').glob('*.db3'));c=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True)
for tid,topic in c.execute("select id,name from topics where name in ('/tf','/tf_static')"):
 for (data,) in c.execute('select data from messages where topic_id=? order by timestamp',(tid,)):
  for t in deserialize_message(data,TFMessage).transforms:(buf.set_transform_static if topic=='/tf_static' else buf.set_transform)(t,'recorded')
old=json.loads((source/'RESULTS.json').read_text());comparisons=[]
with (source/'native_stream.pkl').open('rb') as f:
 i=0
 while True:
  try:m=deserialize_message(pickle.load(f),GridMap)
  except EOFError:break
  ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec;T=matrix(buf.lookup_transform('map','scout_chassis_link',Time(nanoseconds=ns)));o=Odometry();o.header=m.header;o.child_frame_id='base_link';o.pose.pose.position.x,o.pose.pose.position.y,o.pose.pose.position.z=map(float,T[:3,3]);q=Rotation.from_matrix(T[:3,:3]).as_quat();o.pose.pose.orientation.x,o.pose.pose.orientation.y,o.pose.pose.orientation.z,o.pose.pose.orientation.w=map(float,q);clock[0]=ns+30_000_000;n.on_odometry(o);n.on_map(m);assert len(messages)==i+1
  d=layers(messages[-1]);z=np.load(source/'frames'/old['frames'][i]['file']);assert all(np.array_equal(v,z[k],equal_nan=True) for k,v in d.items()),i;comparisons.append({'frame':i,'stamp_ns':ns,'all_published_arrays_exact':True});i+=1
n.destroy_node();rclpy.try_shutdown();c.close();target=O/role;target.mkdir(exist_ok=False);shutil.copytree(C,target/'contexts');rows=[]
for p in sorted(C.glob('*.npz')):
 a=hashlib.sha256(p.read_bytes()).hexdigest();assert a==hashlib.sha256((target/'contexts'/p.name).read_bytes()).hexdigest();rows.append({'file':p.name,'sha256':a,'bytes':p.stat().st_size})
assert len(rows)==len(old['frames'])==117
(target/'CONTEXT_VERIFY.json').write_text(json.dumps({'role':role,'source':str(source),'actual_117_maps_match_exactly':True,'comparisons':comparisons,'files':rows,'capture_schedule_only_modified':True},indent=2)+'\n');print(role,'verified',len(rows),'exact source outputs',flush=True)
