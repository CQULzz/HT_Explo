from pathlib import Path
import sys,json,math
import numpy as np
sys.path.insert(0,'/home/lzz/HT_Explo_ht_only_20261111/tools/cmu_minimal')
from audit_commands import decode
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
sys.path.insert(0,'/home/lzz/pcd_physics_20261110/python')
import pybullet as p
root=Path('/home/lzz/ht_only_20261111/analysis/live_a_stop')
grid=deserialize_message((root/'global_local.cdr').read_bytes(),GridMap);odom=deserialize_message((root/'state_estimation.cdr').read_bytes(),Odometry);m=decode(grid)
position=odom.pose.pose.position;q=odom.pose.pose.orientation;quat=[q.x,q.y,q.z,q.w];R=np.array(p.getMatrixFromQuaternion(quat)).reshape(3,3);yaw=p.getEulerFromQuaternion(quat)[2];x,y=position.x,position.y;r=int(math.floor(m['rows']/2-(x-m['cx'])/m['res']));c=int(math.floor(m['cols']/2-(y-m['cy'])/m['res']))
def layer(name):
 i=grid.layers.index(name);return np.roll(np.array(grid.data[i].data).reshape((m['rows'],m['cols']),order='F'),(-grid.outer_start_index,-grid.inner_start_index),(0,1))
rr,cc=np.where(layer('ht_obstacle')>=.5);xx=m['cx']+(m['rows']/2-rr-.5)*m['res'];yy=m['cy']+(m['cols']/2-cc-.5)*m['res'];dist=np.hypot(xx-x,yy-y);mask=dist<=.45+math.sqrt(2)*m['res']+.03
ob=np.c_[xx[mask],yy[mask],layer('ht_elevation')[rr[mask],cc[mask]],dist[mask]]
p.connect(p.DIRECT);ids=[]
for name in ['ground','obstacles']:
 shape=p.createCollisionShape(p.GEOM_MESH,fileName='/home/lzz/pcd_physics_20261110/assets/'+name+'.obj',flags=p.GEOM_FORCE_CONCAVE_TRIMESH);ids.append(p.createMultiBody(0,shape))
shape=p.createCollisionShape(p.GEOM_BOX,halfExtents=[.3,.2,.15]);body=p.createMultiBody(0,shape,basePosition=(np.array([x,y,position.z])+R@[0,0,-.5]).tolist(),baseOrientation=quat)
contacts=[]
for name,bid in zip(['ground','obstacles'],ids):
 for contact in p.getClosestPoints(body,bid,distance=.05):contacts.append({'mesh':name,'distance_m':contact[8],'point_on_body':contact[5],'point_on_mesh':contact[6]})
p.removeBody(body)
ray=p.rayTestBatch([[float(v[0]),float(v[1]),3.] for v in ob],[[float(v[0]),float(v[1]),-2.] for v in ob]) if len(ob) else []
result={'pose':[x,y,position.z,*p.getEulerFromQuaternion(quat)],'eight_scores':m['scores'][:,r,c].tolist(),'inflated_occupied':bool(m['occupied'][r,c]),'missing':bool(m['missing'][r,c]),'context':float(m['valid'][r,c]),'occupied_cells_within_nearby_inflation':ob.tolist(),'mesh_ray_hits':[{'object_id':v[0],'position':v[3]} for v in ray],'chassis_contacts_within_5cm':contacts,'max_chassis_penetration_m':max([0.]+[-v['distance_m'] for v in contacts]),'model':'Box matching CMU visual body .6x.4x.3m, center sensor+[0,0,-.5], actual recorded full orientation. Static contact query only; not locomotion dynamics or proof of wheel support.'}
(root/'TRUTH.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));p.disconnect()
