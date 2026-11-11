from pathlib import Path
import json,math,heapq,time,sys
import numpy as np
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PointStamped
sys.path.insert(0,'/home/lzz/HT_Explo_ht_only_20261111/tools/cmu_minimal')
from audit_commands import decode
ROOT=Path('/home/lzz/ht_only_20261111');OUT=ROOT/'analysis/live_indoor_stop';meta=json.loads((OUT/'META.json').read_text());selected=deserialize_message((OUT/'global_local.cdr').read_bytes(),GridMap);odom=deserialize_message((OUT/'state_estimation.cdr').read_bytes(),Odometry);way=deserialize_message((OUT/'way_point.cdr').read_bytes(),PointStamped)
m=decode(selected);v=odom.pose.pose.position;q=odom.pose.pose.orientation;x,y=v.x,v.y;yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));goal=np.array([way.point.x,way.point.y]);initial_dist=float(np.linalg.norm(goal-[x,y]));r0=int(np.floor(m['rows']*.5-(x-m['cx'])/m['res']));c0=int(np.floor(m['cols']*.5-(y-m['cy'])/m['res']));k0=int(np.floor((yaw+2*math.pi)/(math.pi/4)+.5))%8
source=Path('/home/lzz/pcd_test_20261110/analysis/static_search/search.py').read_text();block=source[source.index('physical='):source.index('results=[]')].replace('>45','>15');exec(compile(block,'frozen_lattice_search','exec'))
root_allowed=bool(allowed[k0,r0,c0]);results=[]
if root_allowed:
 for progress in [.5,1.,2.]:
  result=solve(progress);results.append(result)
  if not result['found']:break
record={'map_stamp':meta['source_stamp'],'capture_clock':meta['capture_clock'],'start':[x,y,yaw],'goal':goal.tolist(),'eight_scores':m['scores'][:,r0,c0].astype(float).tolist(),'start_full_ht_allowed':root_allowed,'occupied':bool(m['occupied'][r0,c0]),'missing':bool(m['missing'][r0,c0]),'context':float(m['valid'][r0,c0]),'results':results,'scope':'Static original captured HT map; original full-resolution 8-heading forward/reverse/in-place lattice and independent continuous 1cm/1degree recheck. 15s search budget per requested progress. No actuator, braking, future-map or physical contact proof. Search failure is not proof of no continuous-space path.'}
(OUT/'SEARCH.json').write_text(json.dumps(record,indent=2));print({**record,'results':[{k:v for k,v in r.items() if k!='path'} for r in results]})
