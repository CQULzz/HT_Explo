#!/usr/bin/env python3
"""Independently check recorded body-yaw command sweeps against their exact HT map."""
from pathlib import Path
from collections import OrderedDict,Counter
import argparse,json,math
import numpy as np
import cv2
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from std_msgs.msg import String

RADIUS=.45

def key(t):return f'{t:.6f}'
def decode(m):
 rows=round(m.info.length_x/m.info.resolution);cols=round(m.info.length_y/m.info.resolution)
 layers={name:np.roll(np.asarray(data.data,np.float32).reshape((rows,cols),order='F'),(-m.outer_start_index,-m.inner_start_index),(0,1)) for name,data in zip(m.layers,m.data)}
 res=m.info.resolution;n=math.ceil((RADIUS+math.sqrt(2)*res)/res);x,y=np.meshgrid(np.arange(-n,n+1),np.arange(-n,n+1));kernel=(np.hypot(x*res,y*res)<=RADIUS+math.sqrt(2)*res).astype('uint8')
 physical=layers['ht_observation_valid'];obstacle=layers['ht_obstacle']
 missing=cv2.dilate((~np.isfinite(physical)|(physical<.5)).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=1)
 occupied=cv2.dilate((np.isfinite(obstacle)&(obstacle>=.5)).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0)
 raw_occupied=np.isfinite(obstacle)&(obstacle>=.5)
 rr,cc=np.nonzero(raw_occupied)
 return dict(rows=rows,cols=cols,res=res,cx=m.info.pose.position.x,cy=m.info.pose.position.y,scores=np.stack([layers['ht_dir_'+str(i)] for i in range(8)]),valid=layers['ht_valid'],missing=missing,occupied=occupied,raw_occupied=raw_occupied,
             physical=physical,kernel=kernel,obstacle_layer=obstacle,measured=layers.get('ht_measured_valid',np.zeros_like(physical)),stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9,
             obstacle_x=m.info.pose.position.x+(rows*.5-rr-.5)*res,obstacle_y=m.info.pose.position.y+(cols*.5-cc-.5)*res)

def check(m,d):
 if d.get('initial_support_prior_policy')=='explicit_labels_v1' and d.get('initial_support_prior_enabled') and d.get('initial_support_prior_ready'):
  if 'effective' not in m:raise ValueError('Explicit-label history was not reconstructed')
  m=m['effective']
 v=d['linear_candidate'];w=d['angular_candidate']
 if 'reaction_time' in d:
  reaction=d['reaction_time'];av=d['linear_brake_accel'];aw=d['angular_brake_accel'];horizon=reaction+max(abs(v)/av,abs(w)/aw)
  t=np.arange(0,horizon-1e-10,.02);dt=np.minimum(.02,horizon-t);mid=t+dt*.5
  vt=np.sign(v)*np.maximum(0,abs(v)-av*np.maximum(0,mid-reaction));wt=np.sign(w)*np.maximum(0,abs(w)-aw*np.maximum(0,mid-reaction))
  dyaw=wt*dt;before=d['yaw']+np.r_[0,np.cumsum(dyaw)[:-1]]
  x=d['x']+np.r_[0,np.cumsum(vt*dt*np.cos(before+dyaw*.5))];y=d['y']+np.r_[0,np.cumsum(vt*dt*np.sin(before+dyaw*.5))];yaw=d['yaw']+np.r_[0,np.cumsum(dyaw)]
 else:
  t=np.arange(51)*.02;yaw=d['yaw']+w*t
  if abs(w)<1e-8:x=d['x']+v*t*np.cos(d['yaw']);y=d['y']+v*t*np.sin(d['yaw'])
  else:x=d['x']+v/w*(np.sin(yaw)-np.sin(d['yaw']));y=d['y']-v/w*(np.cos(yaw)-np.cos(d['yaw']))
 r=np.floor(m['rows']*.5-(x-m['cx'])/m['res']).astype(int);c=np.floor(m['cols']*.5-(y-m['cy'])/m['res']).astype(int)
 if d['time']<d['map_stamp'] or d['time']-d['map_stamp']>1.:return False,'STALE',None
 if ((r<0)|(c<0)|(r>=m['rows'])|(c>=m['cols'])).any():return False,'OUTSIDE',None
 # Every adjacent 20ms segment is below the production 2cm and pi/64 sample bounds.
 # Therefore these analytic endpoints cover every production sweep sample.
 channel=np.floor((np.arctan2(np.sin(yaw),np.cos(yaw))+2*np.pi)/(np.pi/4)+.5).astype(int)%8
 scores=m['scores'][channel,r,c]
 footprint=d.get('obstacle_footprint','circle_v1')
 if footprint in ('oriented_box_v1','urdf_box_xy_v1'):
  length=float(d['body_length']);width=float(d['body_width']);support=float(d['support_radius'])
  bx=float(d.get('body_center_x',0));by=float(d.get('body_center_y',0))
  reach=math.hypot(abs(bx)+length/2,abs(by)+width/2)
  if not all(math.isfinite(a) and a>0 for a in (length,width,support)) or not all(math.isfinite(a) for a in (bx,by)) or reach>support+1e-8:
   return False,'BODY_CONFIG',None
  if abs(support-RADIUS)>1e-9:raise ValueError('Audit --radius differs from recorded support radius')
  margin=m['res']/math.sqrt(2)+.01+reach*math.pi/128
  # Occupied-cell coordinates are immutable per decoded map. Testing only
  # these cells is equivalent to intersecting the dense rectangle mask with
  # raw_occupied, and avoids rebuilding whole-map arrays for every command.
  gx,gy=m['obstacle_x'],m['obstacle_y']
  for px,py,angle in zip(x,y,yaw):
   dx=gx-px;dy=gy-py;cs=math.cos(angle);sn=math.sin(angle)
   mask=(np.abs(cs*dx+sn*dy-bx)<=length/2+margin)&(np.abs(-sn*dx+cs*dy-by)<=width/2+margin)
   if np.any(mask):return False,'OCCUPIED',float(np.nanmin(scores))
 elif footprint=='circle_v1':
  if m['occupied'][r,c].any():return False,'OCCUPIED',float(np.nanmin(scores))
 else:raise ValueError('Unknown obstacle footprint contract: '+footprint)
 missing=m['missing']
 if d.get('initial_support_prior_enabled',False) and d.get('initial_support_prior_ready',False):
  px,py,pr=[float(d['initial_support_prior_'+k]) for k in ('x','y','radius')]
  if not all(math.isfinite(a) for a in (px,py,pr)) or not 0<pr<=2:raise ValueError('Invalid recorded initial prior')
  prior_key=(px,py,pr)
  if m.get('prior_key')!=prior_key:
   xx=m['cx']+(m['rows']*.5-np.arange(m['rows'])[:,None]-.5)*m['res']
   yy=m['cy']+(m['cols']*.5-np.arange(m['cols'])[None,:]-.5)*m['res']
   prior=np.hypot(xx-px,yy-py)+m['res']/math.sqrt(2)<=pr
   unknown=(~np.isfinite(m['physical'])|(m['physical']<.5))&~prior
   m['prior_missing']=cv2.dilate(unknown.astype('uint8'),m['kernel'],borderType=cv2.BORDER_CONSTANT,borderValue=1)
   m['prior_key']=prior_key
  missing=m['prior_missing']
 if missing[r,c].any():return False,'MISSING',float(np.nanmin(scores))
 if (~np.isfinite(m['valid'][r,c])|(m['valid'][r,c]<.5)).any():return False,'CONTEXT',float(np.nanmin(scores))
 if (~np.isfinite(scores)|(scores<0)|(scores>1)).any():return False,'INVALID_SCORE',None
 return bool((scores>=.5).all()),'SCORE',float(scores.min())

class InitialLabels:
 """Reconstruct explicit startup labels from recorded raw maps, never future maps."""
 def __init__(self,px,py,radius):self.px,self.py,self.radius=px,py,radius;self.labels={};self.last=-float('inf')
 def apply(self,m):
  if m['stamp']<=self.last:return
  self.last=m['stamp'];e=dict(m)
  for k in ['physical','valid','scores','raw_occupied']:e[k]=m[k].copy()
  xx=m['cx']+(m['rows']*.5-np.arange(m['rows'])[:,None]-.5)*m['res'];yy=m['cy']+(m['cols']*.5-np.arange(m['cols'])[None,:]-.5)*m['res']
  xx,yy=np.broadcast_arrays(xx,yy);prior=np.hypot(xx-self.px,yy-self.py)+m['res']/math.sqrt(2)<=self.radius
  actual=0
  for r,c in zip(*np.nonzero(prior)):
   key=(round(float(xx[r,c]/m['res'])),round(float(yy[r,c]/m['res'])))
   blocked=bool(m['raw_occupied'][r,c]);s=m['scores'][:,r,c]
   clear=m['measured'][r,c]>=.5 and m['physical'][r,c]>=.5 and m['valid'][r,c]>=.5 and np.isfinite(m['obstacle_layer'][r,c]) and np.isfinite(s).all() and ((s>=0)&(s<=1)).all()
   fresh=0<=m.get('received',m['stamp'])-m['stamp']<=1.
   if fresh and (blocked or clear):self.labels[key]=(blocked,np.zeros(8,np.float32) if blocked else s.copy())
   if key in self.labels:
    b,s=self.labels[key];actual+=1;e['physical'][r,c]=1;e['valid'][r,c]=1;e['raw_occupied'][r,c]=b;e['scores'][:,r,c]=s
   else:e['physical'][r,c]=1;e['valid'][r,c]=1;e['raw_occupied'][r,c]=False;e['scores'][:,r,c]=1
  rr,cc=np.nonzero(e['raw_occupied']);e['obstacle_x']=xx[rr,cc];e['obstacle_y']=yy[rr,cc]
  e['occupied']=cv2.dilate(e['raw_occupied'].astype('uint8'),m['kernel'],borderType=cv2.BORDER_CONSTANT,borderValue=0)
  e['actual_count']=actual;m['effective']=e

def main():
 p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--radius',type=float,default=.45);a=p.parse_args();run=a.run
 global RADIUS;RADIUS=a.radius
 start=json.loads((run/'observations/START.json').read_text())['clock']
 import csv
 end=float(list(csv.DictReader((run/'observations/metrics.csv').open()))[-1]['time'])
 reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
 reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/ht_minimal/command_audit','/ht_minimal/path_rejection']))
 cache=OrderedDict();pending=[];counts=Counter();examples=[];violations=[];minimum=1.;max_age=0.;label_history=None
 def audit(d):
  nonlocal minimum,max_age,label_history
  if not start<=d['time']<=end:return True
  m=cache.get(key(d['map_stamp']))
  if m is None:return False
  if d.get('initial_support_prior_policy')=='explicit_labels_v1' and d.get('initial_support_prior_enabled') and d.get('initial_support_prior_ready'):
   anchor=tuple(float(d['initial_support_prior_'+k]) for k in ('x','y','radius'))
   if label_history is None:label_history=InitialLabels(*anchor)
   if anchor!=(label_history.px,label_history.py,label_history.radius):raise ValueError('Initial prior anchor changed')
   for raw in cache.values():
    if raw['stamp']<=m['stamp']:label_history.apply(raw)
   if 'effective' not in m or m['effective']['actual_count']!=d['initial_support_actual_cells']:return False
  counts['command_audits']+=1
  if d['allowed']:
   counts['allowed']+=1;max_age=max(max_age,d['time']-d['map_stamp'])
   moving=abs(d['linear_candidate'])>1e-8 or abs(d['angular_candidate'])>1e-8
   counts['allowed_moving']+=moving
   ok,reason,score=check(m,d)
   if score is not None:minimum=min(minimum,score)
   if not ok:
    counts['violations']+=1
    if len(violations)<20:violations.append({**d,'independent_reason':reason,'minimum_score':score})
  else:counts['rejected_'+d['reason']]+=1
  return True
 while reader.has_next():
  topic,data,received=reader.read_next()
  if topic=='/ht_traversability/global_local':
   msg=deserialize_message(data,GridMap);k=key(msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9)
   cache[k]=decode(msg);cache[k]['received']=received/1e9;counts['maps']+=1
   if len(cache)>100:cache.popitem(last=False)
   if pending:
    pending=[d for d in pending if not audit(d)]
  else:
   d=json.loads(deserialize_message(data,String).data)
   if not start<=d.get('time',0)<=end:continue
   if topic=='/ht_minimal/command_audit':
    if not audit(d):pending.append(d)
   else:
    counts['direction_rejection_examples']+=1
    if d['score']<.5<=d['best_direction_score']:
     counts['direction_distinct_rejections']+=1
     m=cache.get(key(d['map_stamp']))
     if m is not None:
      r=int(np.floor(m['rows']*.5-(d['x']-m['cx'])/m['res']));c=int(np.floor(m['cols']*.5-(d['y']-m['cy'])/m['res']))
      if 0<=r<m['rows'] and 0<=c<m['cols']:
       d['recorded_eight_scores']=m['scores'][:,r,c].astype(float).tolist()
       d['recorded_selected_score']=float(m['scores'][d['channel'],r,c]);counts['direction_examples_map_matched']+=1
       if abs(d['recorded_selected_score']-d['score'])>2e-6:counts['direction_score_mismatch']+=1
     if len(examples)<12:examples.append(d)
 counts['unresolved_commands']=len(pending)
 result={'counts':counts,'minimum_allowed_swept_score':minimum,'maximum_allowed_source_age_s':max_age,'examples':examples,'violations':violations,'passed':counts['allowed_moving']>0 and counts['violations']==0 and not pending,'scope':'Exact recorded neural map at each command audit timestamp, recorded reaction plus bounded-braking body-yaw sweep (legacy records use their constant 1s sweep), 0.5 threshold, physical footprint, context and 1-second TTL. Confirms command gate; does not establish learned model ground-truth accuracy.'}
 (run/'COMMAND_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
