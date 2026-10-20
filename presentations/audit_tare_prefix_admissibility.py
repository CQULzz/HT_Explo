#!/usr/bin/env python3
"""Replay the spatial endpoint prefilter on a late recorded HT snapshot (not path feasibility)."""
import argparse,json,math
from pathlib import Path
import cv2,numpy as np,yaml
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Path as RosPath,Odometry
from geometry_msgs.msg import PointStamped
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm


def main():
 ap=argparse.ArgumentParser();ap.add_argument('trial',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 origin=json.loads((a.trial/'current/measurement_started.json').read_text())['wall_time']
 frames=json.loads((a.trial/'snapshots/index.json').read_text())['frames'];frames=[f for f in frames if origin<=f['ht_stamp']<origin+600]
 if not frames:raise ValueError('No recorded in-window snapshot')
 frame=min(frames,key=lambda f:abs(f['ht_stamp']-origin-590));stamp=frame['ht_stamp']
 types={'/tare_route_branch':RosPath,'/tare_native_waypoint':PointStamped,'/state_estimation':Odometry}
 r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(a.trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=list(types)));last={}
 while r.has_next():
  topic,raw,t=r.read_next()
  if t/1e9>stamp:break
  msg=deserialize_message(raw,types[topic])
  if isinstance(msg,RosPath):value=[[p.pose.position.x,p.pose.position.y] for p in msg.poses]
  elif isinstance(msg,Odometry):value=[msg.pose.pose.position.x,msg.pose.pose.position.y]
  else:value=[msg.point.x,msg.point.y]
  last[topic]=dict(stamp=t/1e9,value=value)
 if not last.get('/tare_route_branch',{}).get('value') or '/state_estimation' not in last:raise ValueError('No corresponding native branch/robot')
 params=yaml.safe_load((a.trial/'planner_parameters.yaml').read_text())['/tare_planner_node']['ros__parameters']
 radius=params.get('ht_validity_radius',.6);minimum=params.get('ht_min_probability',.5);configuration=params.get('ht_score_semantics','point')=='configuration'
 with np.load(a.trial/'snapshots'/frame['file']) as d:
  valid=d['ht_ht_valid']>=.5;physical=d['ht_ht_observation_valid']>=.5;occupied=d['ht_ht_obstacle']>=.5;prob=np.stack([d[f'ht_ht_dir_{k}'] for k in range(8)]);cx,cy,res=d['ht_geometry'];rows,cols=valid.shape
 rad=int(np.ceil(radius/res)+1);ii,jj=np.mgrid[-rad:rad+1,-rad:rad+1];kernel=(np.hypot(ii,jj)*res<=radius+np.sqrt(2)*res).astype('uint8')
 unknown=cv2.dilate((~physical).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=1).astype(bool)
 blocked=np.stack([cv2.dilate((occupied if configuration else valid&(p<minimum)).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0).astype(bool)|(valid&(p<minimum)) for p in prob])
 allowed=valid[None]&~unknown[None]&~blocked;any_allowed=np.any(allowed,axis=0)
 branch=np.asarray(last['/tare_route_branch']['value']);robot=np.asarray(last['/state_estimation']['value'])
 def prefix(length):
  for p,q in zip(branch,branch[1:]):
   dist=np.linalg.norm(q-p)
   if dist>1e-9 and dist>=length:return p+(q-p)*(length/dist)
   length-=dist
  return branch[-1]
 tests=[]
 for length in [4.,3.,2.,1.,.5,5.,6.,8.]:
  p=prefix(length);i=int(math.floor(rows*.5-(p[0]-cx)/res));j=int(math.floor(cols*.5-(p[1]-cy)/res));inside=0<=i<rows and 0<=j<cols;dist=float(np.linalg.norm(p-robot));supports=[]
  for k in range(8):
   if not inside:s='UNKNOWN_OUTSIDE'
   elif blocked[k,i,j]:s='BLOCKED'
   elif not valid[i,j] or unknown[i,j]:s='UNKNOWN'
   else:s='KNOWN'
   supports.append(s)
  tests.append(dict(prefix_m=length,original_prefilter_length=length in [4.,3.,2.,1.],xy=p.tolist(),distance_from_robot_m=dist,inside_grid=inside,spatial_support=supports,passes_spatial_prefilter=dist>=.4 and 'KNOWN' in supports))
 result=dict(snapshot_file=frame['file'],measurement_time_s=stamp-origin,record_alignment={k:stamp-v['stamp'] for k,v in last.items()},robot_xy=robot.tolist(),native_waypoint=last.get('/tare_native_waypoint'),score_semantics='configuration' if configuration else 'point',validity_radius_m=radius,min_probability=minimum,tests=tests,all_original_endpoints_rejected=not any(t['passes_spatial_prefilter'] for t in tests if t['original_prefilter_length']),scope='Spatial endpoint gate replay at a recorded snapshot; latest prior branch/odom may differ from exact online cycle. Does not test geometry, swept motions, freshness/startup prior, dynamics or existence of a route. Extra prefix lengths are counterfactual diagnostics only.')
 (a.output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False});fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained');extent=(cx-rows*res/2,cx+rows*res/2,cy-cols*res/2,cy+cols*res/2)
 cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#bfc3c6');axes[0].imshow(np.where(valid,np.nanmax(prob,axis=0),np.nan)[::-1,::-1].T,origin='lower',extent=extent,interpolation='nearest',vmin=0,vmax=1,cmap=cmap);axes[0].set_title('原HT八方向最大分数（不含全足迹门槛）')
 status=np.where(any_allowed,1,np.where(np.any(blocked,axis=0),2,0));axes[1].imshow(status[::-1,::-1].T,origin='lower',extent=extent,interpolation='nearest',cmap=ListedColormap(['#bfc3c6','#16854a','#c93335']),norm=BoundaryNorm([-.5,.5,1.5,2.5],3));axes[1].set_title('至少一个方向通过空间门槛：绿允许/红拒绝/灰未知')
 for ax in axes:
  ax.plot(branch[:,0],branch[:,1],'k-',lw=1,label='TARE选中分支');ax.scatter(*robot,c='blue',s=60,label='车辆')
  for t in tests:
   if not t['original_prefilter_length']:continue
   ax.scatter(*t['xy'],c='orange' if t['passes_spatial_prefilter'] else '#982ab1',s=45);ax.annotate(str(int(t['prefix_m']))+'m',t['xy'],fontsize=9)
  ax.set(xlim=extent[:2],ylim=extent[2:],xlabel='X / m',ylabel='Y / m');ax.legend(fontsize=8)
 fig.suptitle(f'记录快照t={stamp-origin:.1f}s：固定1/2/3/4m局部终点检查；不是搜索可达性证明');fig.savefig(a.output/'endpoints.png',dpi=170);fig.savefig(a.output/'endpoints.pdf');plt.close(fig)
 print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
