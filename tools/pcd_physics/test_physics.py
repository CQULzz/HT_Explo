from pathlib import Path
import sys,math,json,time,csv,hashlib,os,argparse
import numpy as np
sys.path.insert(0,'/home/lzz/pcd_physics_20261110/python')
import pybullet as p
sys.path.insert(0,'/home/lzz/HT_Explo_pcd_20261110/tools/user_pcd')
from prepare import height_at
ROOT=Path('/home/lzz/pcd_physics_20261110');ASSET=ROOT/'assets';manifest=json.loads((ROOT/'MANIFEST.json').read_text());top=np.load('/home/lzz/pcd_test_20261110/source/runtime/scene_meshes.npz')['ground_top'];DT=1/240

def world(flat=False):
 p.resetSimulation();p.setGravity(0,0,-9.81);p.setTimeStep(DT);p.setPhysicsEngineParameter(numSolverIterations=120,deterministicOverlappingPairs=1)
 ids=[]
 if flat:ids.append(p.createMultiBody(0,p.createCollisionShape(p.GEOM_PLANE),basePosition=[0,0,-.8]))
 else:
  for name in ['ground','obstacles']:
   shape=p.createCollisionShape(p.GEOM_MESH,fileName=str(ASSET/f'{name}.obj'),flags=p.GEOM_FORCE_CONCAVE_TRIMESH);visual=p.createVisualShape(p.GEOM_MESH,fileName=str(ASSET/f'{name}.obj'),rgbaColor=[.65,.7,.65,1] if name=='ground' else [.55,.35,.2,1]);ids.append(p.createMultiBody(0,shape,visual))
 for bid in ids:p.changeDynamics(bid,-1,lateralFriction=1.,restitution=0.,collisionMargin=.001)
 return ids

def initial_pose(xy,yaw,flat):
 if flat:return -.8+.23479+.015,0.,0.,{'wheel_ground_z':[-.8]*4,'plane_residual_m':0.}
 offsets=np.array([[.249,.29153],[.249,-.29153],[-.249,.29153],[-.249,-.29153]]);R=np.array([[math.cos(yaw),-math.sin(yaw)],[math.sin(yaw),math.cos(yaw)]]);wheel_xy=xy+offsets@R.T;heights=height_at(wheel_xy,top)
 if any(h is None for h in heights):return None
 plane=np.linalg.lstsq(np.c_[wheel_xy,np.ones(4)],np.array(heights),rcond=None)[0];ax=plane[0]*math.cos(yaw)+plane[1]*math.sin(yaw);ay=-plane[0]*math.sin(yaw)+plane[1]*math.cos(yaw);pitch=-math.atan(ax);roll=math.atan(ay/math.sqrt(1+ax*ax));z=plane@[xy[0],xy[1],1]+.23479*math.sqrt(1+plane[0]**2+plane[1]**2)+.015
 return float(z),roll,pitch,{'wheel_ground_z':heights,'plane':plane.tolist(),'plane_residual_m':float(np.max(abs(np.c_[wheel_xy,np.ones(4)]@plane-heights)))}

def trial(case,gear,friction,label,flat=False,center_only=False):
 out=ROOT/'runs_batch02'/label;out.mkdir(parents=True,exist_ok=False);ids=world(flat);yaw=math.radians(case['heading_deg']);u=np.array([math.cos(yaw),math.sin(yaw)]);n=np.array([-u[1],u[0]]);center=np.array(case['xy']);start=center if center_only else center-gear*.8*u
 result={'case':case,'gear':gear,'friction':friction,'flat_control':flat,'center_only':center_only,'initial_xy':start.tolist(),'desired_center_crossing_length_m':0 if center_only else 1.6,'pybullet_version':'3.2.7','source_manifest_sha256':hashlib.sha256((ROOT/'MANIFEST.json').read_bytes()).hexdigest()}
 init=initial_pose(start,yaw,flat)
 if init is None:
  result.update(status='UNSUPPORTED_INITIAL_WHEEL_LOCATION',passed=False);(out/'RESULT.json').write_text(json.dumps(result,indent=2));return result
 z,roll,pitch,metadata=init;result['initial_geometry']=metadata
 body=p.loadURDF(str(ASSET/'scout.urdf'),[float(start[0]),float(start[1]),z],p.getQuaternionFromEuler([roll,pitch,yaw]),flags=p.URDF_USE_INERTIA_FROM_FILE)
 for link in range(-1,4):p.changeDynamics(body,link,linearDamping=.04,angularDamping=.04,restitution=0.,collisionMargin=.001)
 for j in range(4):
  mu=.8 if friction=='historical_like' else float(friction.split('_')[-1]);anis=[1.,1.,.125] if friction=='historical_like' else [1.,1.,1.];p.changeDynamics(body,j,lateralFriction=mu,anisotropicFriction=anis,spinningFriction=.001,rollingFriction=.001);p.setJointMotorControl2(body,j,p.VELOCITY_CONTROL,targetVelocity=0,force=80)
 names=[p.getJointInfo(body,j)[1].decode() for j in range(4)];result['joint_names']=names
 trace=[];max_body_depth=0.;body_contact_s=0.;max_tilt=0.;crossed=False;maxprogress=-1e9;initial_ok=True;failure=None;stable_start=None;center_crossing=None;v=0.;motion_path=0.;lastxy=None
 total=2. if center_only else 15.
 for step in range(int(total/DT)):
  t=step*DT;pos,q=p.getBasePositionAndOrientation(body);r,pp,yy=p.getEulerFromQuaternion(q);xy=np.array(pos[:2]);tilt=max(abs(r),abs(pp));max_tilt=max(max_tilt,tilt);progress=gear*np.dot(xy-start,u);lateral=np.dot(xy-start,n);maxprogress=max(maxprogress,progress)
  if step==int(2/DT)-1:
   stable_start={'position':list(pos),'rpy':[r,pp,yy],'wheel_contact_count':len({c[3] for c in p.getContactPoints(bodyA=body) if c[3]>=0 and c[9]>1})}
   if tilt>math.radians(30) or pos[2]<z-.35:initial_ok=False;failure='INVALID_SETTLED_START'
  contacts=p.getContactPoints(bodyA=body);base=[c for c in contacts if c[3]==-1 and c[9]>1 and c[8]<-.001]
  if base:
   max_body_depth=max(max_body_depth,max(-c[8] for c in base));body_contact_s+=DT
  if t>=2 and not center_only and failure is None:
   if center_crossing is None and progress>=.8:center_crossing={'xy':xy.tolist(),'lateral_m':float(lateral),'yaw_error_deg':math.degrees(math.atan2(math.sin(yy-yaw),math.cos(yy-yaw)))}
   if progress>=1.6:crossed=True
   command=0. if crossed or t>=14 else .2*gear
   v+=float(np.clip(command-v,-.5*DT,.5*DT));error=math.atan2(math.sin(yaw-yy),math.cos(yaw-yy));w=float(np.clip(1.5*error-gear*.8*lateral,-.35,.35));w=0 if crossed else w
   for j,name in enumerate(names):
    target=(v+(-1 if 'left' in name else 1)*w*.58306/2)/.16459;p.setJointMotorControl2(body,j,p.VELOCITY_CONTROL,targetVelocity=target,force=80)
   if tilt>math.radians(40):failure='TIPPED'
   if pos[2]<-2:failure='FELL_OUT_OF_MEASURED_SUPPORT'
   if abs(lateral)>.5:failure='LEFT_PROBE_CORRIDOR'
  if lastxy is not None:motion_path+=np.linalg.norm(xy-lastxy)
  lastxy=xy
  if step%12==0:trace.append({'time_s':t,'x':pos[0],'y':pos[1],'z':pos[2],'roll':r,'pitch':pp,'yaw':yy,'progress_m':progress,'lateral_m':lateral,'chassis_contacts':len(base),'wheel_contact_count':len({c[3] for c in contacts if c[3]>=0 and c[9]>1}),**{f'joint_{j}_angle':p.getJointState(body,j)[0] for j in range(4)}})
  if failure is not None and t>=2:
   for j in range(4):p.setJointMotorControl2(body,j,p.VELOCITY_CONTROL,targetVelocity=0,force=80)
  p.stepSimulation()
  if failure and t>2.1:break
 pose_matched=center_only or (center_crossing is not None and abs(center_crossing['lateral_m'])<=.1 and abs(center_crossing['yaw_error_deg'])<=15)
 if crossed and not pose_matched and failure is None:failure='MISSED_REQUESTED_CENTER_POSE'
 result.update(center_crossing=center_crossing,status=('CENTER_SETTLED' if initial_ok and failure is None else failure) if center_only else (failure or ('CROSSED' if crossed else 'DID_NOT_CROSS')),
  passed=bool(initial_ok and failure is None and (center_only or crossed)),crossed=bool(crossed),maximum_progress_m=float(maxprogress),actual_path_m=float(motion_path),chassis_contact_s=body_contact_s,max_chassis_penetration_m=max_body_depth,max_tilt_deg=math.degrees(max_tilt),settled_start=stable_start,final_pose=trace[-1] if trace else None,clean_pass=bool(initial_ok and failure is None and (center_only or crossed) and max_body_depth<.005 and body_contact_s<.25))
 with (out/'trace.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(trace[0]));writer.writeheader();writer.writerows(trace)
 (out/'RESULT.json').write_text(json.dumps(result,indent=2));return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');args=parser.parse_args();p.connect(p.DIRECT);results=[]
 if args.pilot:
  c={'id':'flat_control','class':'control','xy':[0.,0.],'heading_deg':0.,'ht_score':None};results.append(trial(c,1,'historical_like','pilot_flat',True))
  c={'id':'map_spawn_control','class':'control','xy':[.1102345,.1362935],'heading_deg':0.,'ht_score':None};results.append(trial(c,1,'historical_like','pilot_map'))
 else:
  for mode in ['historical_like','isotropic_0.4','isotropic_0.8']:
   c={'id':'flat_control','class':'control','xy':[0.,0.],'heading_deg':0.,'ht_score':None};r=trial(c,1,mode,'flat_'+mode,True);results.append(r);print(r['case']['id'],mode,r['status'],r['maximum_progress_m'],flush=True)
   for c in manifest['selected_cases']:
    center_result=trial(c,1,mode,f'{c["id"]}_{mode}_center',center_only=True);results.append(center_result);print(c['id'],mode,'center',center_result['status'],flush=True)
    for gear in [1,-1]:
     name=f'{c["id"]}_{mode}_{"fwd" if gear==1 else "rev"}';r=trial(c,gear,mode,name);results.append(r);print(c['id'],mode,gear,r['status'],r.get('maximum_progress_m'),flush=True)
  (ROOT/'RESULTS.json').write_text(json.dumps(results,indent=2))
 p.disconnect();print(json.dumps([{k:r.get(k) for k in ['status','passed','clean_pass','maximum_progress_m','chassis_contact_s','max_tilt_deg','settled_start']} for r in results],indent=2))
if __name__=='__main__':main()
