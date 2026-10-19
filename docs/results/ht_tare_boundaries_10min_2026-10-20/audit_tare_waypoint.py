#!/usr/bin/env python3
"""Audit native TARE order/waypoint -> same-branch HT routing in a recorded run."""
import argparse,json,re,csv
from pathlib import Path
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Path as RosPath,Odometry
from geometry_msgs.msg import PointStamped
from std_msgs.msg import Bool,String
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
 ap=argparse.ArgumentParser();ap.add_argument('trial',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 args.output.mkdir(parents=True,exist_ok=True)
 origin=json.loads((args.trial/'current/measurement_started.json').read_text())['wall_time']
 types={'/tare_coverage_route':RosPath,'/tare_route_branch':RosPath,'/ht_xytheta_path':RosPath,
        '/tare_native_waypoint':PointStamped,'/ht_route_goal':PointStamped,'/way_point':PointStamped,
        '/ht_navigation_allowed':Bool,'/tare_tsp_order':String,'/state_estimation':Odometry}
 reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(args.trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
 reader.set_filter(rosbag2_py.StorageFilter(topics=list(types)))
 counts={k:0 for k in types};latest={};snapshots=[];orders=[];violations=[];moving_waypoints=0;prefixes=0;track=[];route_times=[]
 def xy(p):return [float(p.x),float(p.y)]
 while reader.has_next():
  topic,raw,stamp=reader.read_next();t=stamp/1e9-origin
  if t<0 or t>600:continue
  msg=deserialize_message(raw,types[topic]);counts[topic]+=1
  if isinstance(msg,RosPath):value=[xy(p.pose.position) for p in msg.poses]
  elif isinstance(msg,PointStamped):value=xy(msg.point)
  elif isinstance(msg,Odometry):value=xy(msg.pose.pose.position)
  else:value=msg.data
  latest[topic]=(t,value)
  if topic=='/state_estimation':track.append([t,*value])
  elif topic=='/tare_coverage_route':route_times.append(t)
  elif topic=='/tare_tsp_order':
   ids=json.loads(value);orders.append(dict(time_s=t,count=len(ids),order=ids))
  elif topic=='/way_point' and latest.get('/ht_navigation_allowed',(0,False))[1]:
   moving_waypoints+=1
   goal=latest.get('/tare_native_waypoint')
   if goal is None or np.linalg.norm(np.subtract(value,goal[1]))>1e-4:violations.append(dict(time_s=t,kind='moving_waypoint_differs_from_native',waypoint=value,native=goal))
  elif topic=='/ht_route_goal':
   prefixes+=1;branch=latest.get('/tare_route_branch',(0,[]))[1]
   distances=[]
   for a,b in zip(branch,branch[1:]):
    a=np.asarray(a);b=np.asarray(b);d=b-a;u=np.clip(np.dot(np.asarray(value)-a,d)/max(np.dot(d,d),1e-12),0,1)
    distances.append(np.linalg.norm(np.asarray(value)-(a+u*d)))
   if not distances or min(distances)>1e-4:violations.append(dict(time_s=t,kind='local_goal_off_selected_branch',goal=value))
  elif topic=='/ht_xytheta_path' and len(value)>1:
   snapshots.append(dict(time_s=t,route=latest.get('/tare_coverage_route',(0,[]))[1],branch=latest.get('/tare_route_branch',(0,[]))[1],
     native=latest.get('/tare_native_waypoint',(0,[]))[1],local=latest.get('/ht_route_goal',(0,[]))[1],path=value,robot=latest.get('/state_estimation',(0,[]))[1]))
 text=(args.trial/'current/tare.log').read_text(errors='replace');cycles=[];searches=[]
 for line in text.splitlines():
  clock=re.search(r'\[(\d+\.\d+)\]',line);t=float(clock[1])-origin if clock else -1
  if not 0<=t<=600:continue
  match=re.search(r'TARE_COVERAGE native=1 tsp_calls=(\d+) iterations=(\d+) selected=(\d+) route_nodes=(\d+) route_length=([\d.]+) complete=(\d+)',line)
  if match:cycles.append(dict(time_s=t,tsp_calls=int(match[1]),iterations=int(match[2]),selected=int(match[3]),route_nodes=int(match[4]),route_length=float(match[5]),complete=int(match[6])))
  match=re.search(r'HT_WAYPOINT_SEARCH.*reached=(\d+) termination=(\w+).*expanded=(\d+) direct=(\d+) pruned=(\d+)',line)
  if match:searches.append(dict(time_s=t,reached=int(match[1]),termination=match[2],expanded=int(match[3]),direct=int(match[4]),pruned=int(match[5])))
 from collections import Counter
 summary=dict(message_counts=counts,coverage_cycles=len(cycles),tsp_calls=Counter(c['tsp_calls'] for c in cycles),
  maximum_ordered_viewpoints=max([v['count'] for v in orders],default=0),mean_ordered_viewpoints=float(np.mean([v['count'] for v in orders])) if orders else 0,
  moving_waypoints=moving_waypoints,local_goals=prefixes,nonempty_executable_paths=len(snapshots),searches=len(searches),search_termination=Counter(s['termination'] for s in searches),
  contract_violations=violations,contract_passed=bool(cycles and orders and moving_waypoints and snapshots) and not violations,
  scope='Sampled/message-level contract, not a proof of global exploration optimality or continuous physical safety.')
 (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 for name,data in [('cycles',cycles),('orders',orders),('searches',searches),('routing_snapshots',snapshots)]:
  (args.output/(name+'.json')).write_text(json.dumps(data,separators=(',',':'))+'\n')
 plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
 fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained')
 if cycles:
  axes[0,0].plot([c['time_s'] for c in cycles],[c['selected'] for c in cycles],label='TARE完整访问序列长度')
  axes[0,0].set(ylabel='视点数',xlabel='测量时间 / s');axes[0,0].legend()
  axes[0,1].step([c['time_s'] for c in cycles],[c['tsp_calls'] for c in cycles],where='post',label='本周期原TSP调用次数')
  axes[0,1].set(ylabel='调用次数',xlabel='测量时间 / s');axes[0,1].legend()
 if track:
  a=np.asarray(track);axes[1,0].plot(a[:,1],a[:,2],label='实际里程计轨迹');axes[1,0].set_aspect('equal',adjustable='datalim');axes[1,0].set(xlabel='X / m',ylabel='Y / m');axes[1,0].legend()
 if searches:
  for key in sorted(set(s['termination'] for s in searches)):
   items=[s for s in searches if s['termination']==key];axes[1,1].scatter([s['time_s'] for s in items],[s['expanded'] for s in items],s=10,label=key)
  axes[1,1].set(xlabel='测量时间 / s',ylabel='XYθ展开数');axes[1,1].legend()
 fig.suptitle('原TARE负责访问顺序，HT负责当前航点的局部可执行路径');fig.savefig(args.output/'architecture.png',dpi=150);fig.savefig(args.output/'architecture.pdf');plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(13,11),layout='constrained')
 for ax,target in zip(axes.flat,[30,150,300,550]):
  if not snapshots:continue
  s=min(snapshots,key=lambda s:abs(s['time_s']-target));
  for key,label,color,style in [('route','TARE完整覆盖序列','#a5a5a5','--'),('branch','TARE选中分支','#e6a329','-'),('path','HT实际执行XYθ投影','#1677ba','-')]:
   a=np.asarray(s[key]);
   if len(a):ax.plot(a[:,0],a[:,1],style,label=label,color=color,lw=1.4 if key=='route' else 2)
  for key,marker,label,color in [('native','*','原版延伸航点','#c33437'),('local','s','同分支局部目标','#963baf'),('robot','o','车辆','#16854a')]:
   if s[key]:ax.scatter(*s[key],marker=marker,s=75,c=color,label=label,zorder=5)
  ax.set(title=f't={s["time_s"]:.1f}s',xlabel='X / m',ylabel='Y / m');ax.set_aspect('equal',adjustable='datalim');ax.legend(fontsize=8)
 fig.suptitle('记录中的访问序列、当前航点与HT路由（灰线含未来视点，不是执行轨迹）');fig.savefig(args.output/'routes.png',dpi=160);fig.savefig(args.output/'routes.pdf');plt.close(fig)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
