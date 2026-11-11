"""Read-only mesh contact queries at recorded CMU poses, no dynamic integration."""
from pathlib import Path
import sys,json,math,argparse,xml.etree.ElementTree as ET,hashlib
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry
sys.path.insert(0,'/home/lzz/pcd_physics_20261110/python')
import pybullet as p
ap=argparse.ArgumentParser();ap.add_argument('run',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();out=a.output or a.run/'mesh_contact';out.mkdir(exist_ok=False)
start=json.loads((a.run/'observations/START.json').read_text())['clock'];import csv
end=float(list(csv.DictReader((a.run/'observations/metrics.csv').open()))[-1]['time'])
sdf=Path('/home/lzz/cmu_test_20261110/common_sensor/robot.sdf');visual=next(v for v in ET.parse(sdf).findall('.//visual') if 'base_link_visual' in v.attrib.get('name',''));size=np.fromstring(visual.findtext('geometry/box/size'),sep=' ');offset=np.fromstring(visual.findtext('pose'),sep=' ')[:3]
p.connect(p.DIRECT);ids=[]
for name in ['ground','obstacles']:
 path=Path('/home/lzz/pcd_physics_20261110/assets')/(name+'.obj');shape=p.createCollisionShape(p.GEOM_MESH,fileName=str(path),flags=p.GEOM_FORCE_CONCAVE_TRIMESH);ids.append(p.createMultiBody(0,shape))
shape=p.createCollisionShape(p.GEOM_BOX,halfExtents=(size/2).tolist());body=p.createMultiBody(0,shape);p.changeDynamics(body,-1,collisionMargin=.001)
reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(a.run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/state_estimation']))
poses=[];examples=[];last=None;maximum=0;maxground=0;maxobs=0;read_count=0
while reader.has_next():
 _,data,received=reader.read_next();m=deserialize_message(data,Odometry);stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
 if not start<=stamp<=end:continue
 read_count+=1;v=m.pose.pose.position;q=m.pose.pose.orientation;quat=[q.x,q.y,q.z,q.w];rpy=p.getEulerFromQuaternion(quat);xyz=np.array([v.x,v.y,v.z]);yaw=rpy[2]
 if last is not None and np.linalg.norm(xyz-last[1])<.01 and abs(math.atan2(math.sin(yaw-last[2]),math.cos(yaw-last[2])))<math.pi/180 and stamp-last[0]<1:continue
 last=(stamp,xyz,yaw);center=xyz+np.array(p.getMatrixFromQuaternion(quat)).reshape(3,3)@offset;p.resetBasePositionAndOrientation(body,center,quat)
 depths=[]
 for bid in ids:
  contacts=p.getClosestPoints(body,bid,distance=0.01);depths.append(max([0.]+[-c[8] for c in contacts]))
 maximum=max(maximum,*depths);maxground=max(maxground,depths[0]);maxobs=max(maxobs,depths[1]);poses.append([stamp-start,*xyz,*rpy,*depths])
 if max(depths)>.005 and len(examples)<40:examples.append(poses[-1])
p.disconnect();np.savez_compressed(out/'samples.npz',poses=np.array(poses),columns=np.array(['elapsed_s','x','y','sensor_z','roll','pitch','yaw','ground_penetration_m','obstacle_penetration_m']))
result={'source_sdf':str(sdf),'source_sdf_sha256':hashlib.sha256(sdf.read_bytes()).hexdigest(),'chassis_size_m':size.tolist(),'sensor_to_chassis_center_m':offset.tolist(),'recorded_odometry_count':read_count,'sampled_pose_count':len(poses),'penetrating_samples_over_5mm':sum(max(v[-2:])>.005 for v in poses),'max_chassis_penetration_m':maximum,'max_ground_penetration_m':maxground,'max_obstacle_penetration_m':maxobs,'examples':examples,'scope':'Static box contacts at recorded full CMU poses, same dimensions as CMU visual chassis and exact original meshes. Samples at >=1cm or >=1degree changes or 1second; not a guarantee between sampled poses. No wheel contact dynamics, no motor integration, and no real-vehicle validation. Used as independent evaluation, never fed into navigation.'}
(out/'RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
