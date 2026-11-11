from pathlib import Path
import json,time,subprocess,os,signal,math
import numpy as np
from scipy.spatial.transform import Rotation
import rclpy,rosbag2_py
from rclpy.node import Node
from rclpy.serialization import deserialize_message,serialize_message
from nav_msgs.msg import Odometry,Path as RosPath
from geometry_msgs.msg import PointStamped,PolygonStamped,Point32,TwistStamped
from std_msgs.msg import String
from grid_map_msgs.msg import GridMap
from sensor_msgs.msg import PointCloud2
from rosgraph_msgs.msg import Clock
ROOT=Path('/home/lzz/pcd_test_20261110');SOURCE=ROOT/'analysis/static_search';OUT=Path('/home/lzz/ht_only_20261111/analysis/replay_a');OUT.mkdir(exist_ok=False)
analysis=json.loads((SOURCE/'RESULT.json').read_text());d=analysis['source_command_audit'];t=d['time']
topics={'/terrain_map':PointCloud2,'/state_estimation':Odometry,'/ht_traversability/global_local':GridMap}
last={topic:deserialize_message((SOURCE/(topic.rsplit('/',1)[-1]+'.cdr')).read_bytes(),cls) for topic,cls in topics.items()};grid=last['/ht_traversability/global_local']
rclpy.init();result={}
for label,targetyaw,mode in [('geometry_only',d['yaw'],'geometry_only'),('geometry_and_ht',d['yaw'],'geometry_and_ht'),('ht_only',d['yaw'],'ht_only'),('ht_only_turned_135',3*math.pi/4,'ht_only')]:
 node=Node('static_replay_'+label);pubs={topic:node.create_publisher(cls,topic,10) for topic,cls in topics.items()};clock=node.create_publisher(Clock,'/clock',10);goalpub=node.create_publisher(PointStamped,'/way_point',10);bound=node.create_publisher(PolygonStamped,'/navigation_boundary',10);paths=[];commands=[];selections=[]
 node.create_subscription(RosPath,'/path',lambda m:paths.append({'poses':[[p.pose.position.x,p.pose.position.y,p.pose.position.z] for p in m.poses],'stamp':m.header.stamp.sec+m.header.stamp.nanosec*1e-9}),100)
 node.create_subscription(TwistStamped,'/cmd_vel',lambda m:commands.append([m.twist.linear.x,m.twist.angular.z]),100)
 node.create_subscription(String,'/ht_minimal/local_selection',lambda m:selections.append(json.loads(m.data)),100)
 logfile=(OUT/(label+'_planner.log')).open('w');proc=subprocess.Popen(['/home/lzz/ht_only_20261111/install_gate/cmu_local_planner_ht/lib/cmu_local_planner_ht/localPlanner','--ros-args','--params-file',str(ROOT/'runs/user_pcd_8dir_600s_01/localPlanner.yaml'),'-p','use_sim_time:=true','-p','traversability_mode:='+mode,'-p','require_navigation_boundary:=true'],stdout=logfile,stderr=subprocess.STDOUT,start_new_session=True)
 followerlog=(OUT/(label+'_follower.log')).open('w');follower=subprocess.Popen(['/home/lzz/ht_only_20261111/install_gate/cmu_local_planner_ht/lib/cmu_local_planner_ht/pathFollower','--ros-args','--params-file',str(ROOT/'runs/user_pcd_8dir_600s_01/pathFollower.yaml'),'-p','use_sim_time:=true','-p','traversability_mode:='+mode,'-p','require_navigation_boundary:=true'],stdout=followerlog,stderr=subprocess.STDOUT,start_new_session=True)
 def send_clock(t):
  m=Clock();m.clock.sec=int(t);m.clock.nanosec=int((t-int(t))*1e9);clock.publish(m)
 try:
  deadline=time.monotonic()+20
  while time.monotonic()<deadline:
   send_clock(t);rclpy.spin_once(node,timeout_sec=.03)
   if 'Initialization complete.' in (OUT/(label+'_planner.log')).read_text(errors='replace'):break
  else:raise RuntimeError('Planner not initialized')
  odom=deserialize_message(serialize_message(last['/state_estimation']),Odometry);q=odom.pose.pose.orientation;angles=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_euler('xyz');angles[2]=targetyaw;qq=Rotation.from_euler('xyz',angles).as_quat();q.x,q.y,q.z,q.w=map(float,qq)
  goal=PointStamped();goal.header=odom.header;goal.point.x=analysis['goal'][0];goal.point.y=analysis['goal'][1];goal.point.z=odom.pose.pose.position.z
  polygon=PolygonStamped();polygon.header=odom.header;polygon.polygon.points=[Point32(x=float(x),y=float(y),z=0.) for x,y in [(-13.5,-13.5),(13.5,-13.5),(13.5,13.5),(-13.5,13.5)]]
  for i in range(60):
   send_clock(t+i*.01);pubs['/state_estimation'].publish(odom);goalpub.publish(goal)
   if i%5==0:
    pubs['/terrain_map'].publish(last['/terrain_map']);pubs['/ht_traversability/global_local'].publish(grid);bound.publish(polygon)
   rclpy.spin_once(node,timeout_sec=.01);time.sleep(.01)
  for _ in range(10):rclpy.spin_once(node,timeout_sec=.01)
  lengths=[len(p['poses']) for p in paths];result[label]={'yaw_deg':math.degrees(targetyaw),'received_paths':len(paths),'max_path_pose_count':max(lengths,default=0),'nontrivial_paths':sum(n>1 for n in lengths),'paths':paths,'commands':commands,'nonzero_commands':sum(abs(v)+abs(w)>1e-8 for v,w in commands),'selections':selections}
 finally:
  os.killpg(proc.pid,signal.SIGINT)
  try:proc.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
  os.killpg(follower.pid,signal.SIGINT)
  try:follower.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(follower.pid,signal.SIGKILL);follower.wait()
  result[label]['exit_codes']={'planner':proc.returncode,'follower':follower.returncode}
  logfile.close();followerlog.close();node.destroy_node()
rclpy.shutdown();(OUT/'REPLAY_RESULT.json').write_text(json.dumps({'results':result,'scope':'Counterfactual static-input replay of candidate A localPlanner plus pathFollower, no vehicle/actuator. Recorded terrain and exact HT map, original odometry except hypothetical yaw in turned case, original goal and boundary. ROS replay clock advances 0.59s from original recorded audit; measurement source stamps unchanged. This is not closed-loop execution.'},indent=2));print({k:{kk:vv for kk,vv in v.items() if kk not in ['paths','commands','selections']} for k,v in result.items()})
