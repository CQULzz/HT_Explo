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
 return dict(rows=rows,cols=cols,res=res,cx=m.info.pose.position.x,cy=m.info.pose.position.y,scores=np.stack([layers['ht_dir_'+str(i)] for i in range(8)]),valid=layers['ht_valid'],missing=missing,occupied=occupied,raw_occupied=np.isfinite(obstacle)&(obstacle>=.5))

def check(m,d):
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
 if footprint=='oriented_box_v1':
  length=float(d['body_length']);width=float(d['body_width']);support=float(d['support_radius'])
  if not all(math.isfinite(a) and a>0 for a in (length,width,support)) or math.hypot(length/2,width/2)>support+1e-9:
   return False,'BODY_CONFIG',None
  if abs(support-RADIUS)>1e-9:raise ValueError('Audit --radius differs from recorded support radius')
  margin=m['res']/math.sqrt(2)+.01+math.hypot(length/2,width/2)*math.pi/128
  rr,cc=np.indices((m['rows'],m['cols']))
  gx=m['cx']+(m['rows']*.5-rr-.5)*m['res'];gy=m['cy']+(m['cols']*.5-cc-.5)*m['res']
  for px,py,angle in zip(x,y,yaw):
   dx=gx-px;dy=gy-py;cs=math.cos(angle);sn=math.sin(angle)
   mask=(np.abs(cs*dx+sn*dy)<=length/2+margin)&(np.abs(-sn*dx+cs*dy)<=width/2+margin)
   if np.any(mask&m['raw_occupied']):return False,'OCCUPIED',float(np.nanmin(scores))
 elif footprint=='circle_v1':
  if m['occupied'][r,c].any():return False,'OCCUPIED',float(np.nanmin(scores))
 else:raise ValueError('Unknown obstacle footprint contract: '+footprint)
 if m['missing'][r,c].any():return False,'MISSING',float(np.nanmin(scores))
 if (~np.isfinite(m['valid'][r,c])|(m['valid'][r,c]<.5)).any():return False,'CONTEXT',float(np.nanmin(scores))
 if (~np.isfinite(scores)|(scores<0)|(scores>1)).any():return False,'INVALID_SCORE',None
 return bool((scores>=.5).all()),'SCORE',float(scores.min())

def main():
 p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--radius',type=float,default=.45);a=p.parse_args();run=a.run
 global RADIUS;RADIUS=a.radius
 start=json.loads((run/'observations/START.json').read_text())['clock']
 import csv
 end=float(list(csv.DictReader((run/'observations/metrics.csv').open()))[-1]['time'])
 reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
 reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/ht_minimal/command_audit','/ht_minimal/path_rejection']))
 cache=OrderedDict();pending=[];counts=Counter();examples=[];violations=[];minimum=1.;max_age=0.
 def audit(d):
  nonlocal minimum,max_age
  if not start<=d['time']<=end:return True
  m=cache.get(key(d['map_stamp']))
  if m is None:return False
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
   cache[k]=decode(msg);counts['maps']+=1
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
